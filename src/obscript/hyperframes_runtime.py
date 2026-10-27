"""One installed HyperFrames CLI/Studio, with independent composition folders."""
from __future__ import annotations

import fcntl
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


HYPERFRAMES_VERSION = "0.8.169"
LAUNCHER = Path(__file__).resolve().parents[2] / "bin/obscript-hyperframes"
PROJECT_NOTICE_START = "<!-- obscript-runtime:start -->"
PROJECT_NOTICE_END = "<!-- obscript-runtime:end -->"


class HyperframesRuntimeError(RuntimeError):
    pass


def runtime_directory() -> Path:
    override = os.environ.get("OBSCRIPT_HYPERFRAMES_HOME")
    cache = Path(os.environ.get("XDG_CACHE_HOME") or "~/.cache").expanduser()
    return (Path(override).expanduser() if override else cache / "obscript/hyperframes").resolve()


def runtime_handoff() -> dict:
    return {
        "directory": str(runtime_directory()), "version": HYPERFRAMES_VERSION,
        "command": [str(LAUNCHER)], "install_scope": "shared",
        "project_dependencies": False,
    }


def runtime_instructions() -> str:
    command = shlex.quote(str(LAUNCHER))
    return f"""Use the shared HyperFrames CLI and Studio through {command} for every HyperFrames command.
Run it from the editable project directory for check, preview, render, catalog, skills, and history.
To scaffold, run {command} init <project_directory> --non-interactive --skill=general-video.
This wrapper replaces npx hyperframes and pinned npx commands in installed skill instructions.
The application manages the shared runtime version. Do not run HyperFrames upgrade, install
HyperFrames or Studio in a project, run npm install/ci, copy node_modules, or build Studio locally.
Keep project HTML, compositions, assets, and outputs local; use the prebuilt shared Studio.
"""


def _installed_cli(directory: Path) -> Path | None:
    package = directory / "node_modules/hyperframes"
    try:
        manifest = json.loads((package / "package.json").read_text(encoding="utf-8"))
        if manifest.get("version") != HYPERFRAMES_VERSION:
            return None
        entry = manifest["bin"]
        if isinstance(entry, dict):
            entry = entry["hyperframes"]
        cli = (package / entry).resolve()
        if (not cli.is_relative_to(package.resolve()) or not cli.is_file()
                or not (package / "dist/studio/index.html").is_file()):
            return None
        return cli
    except (OSError, ValueError, KeyError, TypeError):
        return None


def ensure_runtime() -> Path:
    """Bootstrap before launching a sandboxed agent; reuse without writes thereafter."""
    directory = runtime_directory()
    cli = _ready_cli(directory)
    if cli is not None:
        return cli
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".install.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cli = _ready_cli(directory)
        if cli is not None:
            return cli
        if not shutil.which("node") or not shutil.which("npm"):
            raise HyperframesRuntimeError("Node.js >=22 and npm are required for the shared HyperFrames runtime")
        (directory / ".ready").unlink(missing_ok=True)
        print(f"[obscript] Installing shared HyperFrames {HYPERFRAMES_VERSION} in {directory}",
              file=sys.stderr, flush=True)
        # npm installs only here. No npx cache or project-local dependency trees.
        manifest_path = directory / "package.json"
        if not manifest_path.exists():
            manifest_path.write_text('{"name":"obscript-hyperframes-runtime","private":true}\n', encoding="utf-8")
        try:
            result = subprocess.run(
                ["npm", "install", "--prefix", str(directory), "--save-exact", "--no-audit", "--no-fund",
                 f"hyperframes@{HYPERFRAMES_VERSION}"],
                cwd=directory, capture_output=True, text=True, check=False,
            )
        except OSError as exc:
            raise HyperframesRuntimeError(f"Cannot install shared HyperFrames: {exc}") from exc
        log = directory / "install.log"
        log.write_text((result.stdout or "") + (result.stderr or ""), encoding="utf-8")
        cli = _installed_cli(directory)
        if result.returncode or cli is None:
            raise HyperframesRuntimeError(f"Shared HyperFrames installation failed; see {log}")
        (directory / ".ready").write_text(HYPERFRAMES_VERSION, encoding="utf-8")
        return cli


def _ready_cli(directory: Path) -> Path | None:
    # npm unpacks the CLI before all dependencies are installed. Publish readiness
    # only after the installer exits successfully, so parallel agents cannot race it.
    try:
        if (directory / ".ready").read_text(encoding="utf-8") != HYPERFRAMES_VERSION:
            return None
    except OSError:
        return None
    return _installed_cli(directory)


def prepare_project(project: Path) -> None:
    """Replace scaffolded npx scripts while preserving authored project content."""
    if not project.is_dir():
        return
    package = project / "package.json"
    if package.is_file():
        data = json.loads(package.read_text(encoding="utf-8"))
        original = json.dumps(data, sort_keys=True)
        # Retain custom script arguments and unrelated tools/dependencies.
        pattern = r"(^|(?:&&|\|\||[;|])\s*)(?:npx\s+(?:(?:--yes|-y)\s+)?hyperframes(?:@[^\s;&|]+)?|hyperframes)(?=\s|$)"
        command = shlex.quote(str(LAUNCHER))
        for name, script in data.get("scripts", {}).items():
            data["scripts"][name] = re.sub(pattern, lambda match: match[1] + command, script)
        for section in ("dependencies", "devDependencies"):
            data.get(section, {}).pop("hyperframes", None)
        if json.dumps(data, sort_keys=True) != original:
            package.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    agents = project / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.exists() else ""
    text = re.sub(re.escape(PROJECT_NOTICE_START) + r".*?" + re.escape(PROJECT_NOTICE_END) + r"\n*",
                  "", text, flags=re.DOTALL)
    notice = f"{PROJECT_NOTICE_START}\n{runtime_instructions()}{PROJECT_NOTICE_END}\n\n"
    updated = notice + text
    if not agents.exists() or agents.read_text(encoding="utf-8") != updated:
        agents.write_text(updated, encoding="utf-8")


def copy_project(source: Path, destination: Path) -> None:
    """Copy editable sources and media without duplicating installed tooling."""
    shutil.copytree(source, destination, symlinks=True,
                    ignore=shutil.ignore_patterns("node_modules", ".git", ".npm", ".cache", "__pycache__"))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        cli = ensure_runtime()
        # Do not allow skill-driven upgrades to create a second runtime via npx.
        if args and args[0] == "upgrade":
            raise HyperframesRuntimeError("HyperFrames is pinned by obscript; update the shared runtime through obscript")
        project = None
        if args and args[0] == "init" and not any(flag in args for flag in ("--help", "-h")):
            if len(args) < 2 or args[1].startswith("-"):
                raise HyperframesRuntimeError("Use: obscript-hyperframes init PROJECT_DIRECTORY [options]")
            project = Path(args[1]).resolve()
        result = subprocess.run(["node", str(cli), *args], check=False)
        if not result.returncode and project is not None:
            prepare_project(project)
        return result.returncode
    except (HyperframesRuntimeError, OSError, ValueError, TypeError) as exc:
        print(f"obscript-hyperframes: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
