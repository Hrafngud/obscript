from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from . import __version__
from .agent import AgentError
from .contracts import ContractError, parse_command_tokens, parse_duration
from .models import CommandSpec, RuntimeConfig
from .pipeline import Pipeline
from .production import ProductionError
from .projects import create_original_project, find_project, resume_spec
from .storage import read_json
from .transcribe import TranscriptionError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obscript",
        description="Generate original PT-BR scripts, visual pre-production, and optional silent HyperFrames animations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""ordered grammar:
  obscript [remix|split] [compress|extend] [topics|essay] <source>
  obscript new [TITLE] [--format topics|essay] [--target-duration DURATION]

examples:
  obscript new
  obscript new "Minha ideia" --target-duration 8m
  obscript VIDEO
  obscript compress essay VIDEO
  obscript remix extend topics VIDEO_A,VIDEO_B
  obscript split compress essay VIDEO --target-duration 8m
  obscript split topics VIDEO --into 4
  obscript extend essay VIDEO --render
  obscript VIDEO --storybook
  obscript PROJECT_ID --render
  obscript VIDEO --render --opencode
  obscript PROJECT_ID --render --opencode
  obscript PROJECT_ID --post-production

For remix, comma-separate sources inside one shell argument. PT-BR normalization
is mandatory and has no translate modifier.
""",
    )
    parser.add_argument(
        "command",
        nargs="+",
        metavar="COMMAND",
        help="new [TITLE], ordered modifiers followed by a source, or an existing project ID",
    )
    parser.add_argument(
        "--target-duration",
        metavar="DURATION",
        help="target such as 480, 8m, 1.5h, or 08:00",
    )
    parser.add_argument("--into", type=int, metavar="COUNT", help="desired split count")
    parser.add_argument("--project", help="Obsidian project folder name")
    parser.add_argument("--format", choices=["source", "topics", "essay"],
                        help="format metadata for a new manual script (default: topics)")
    parser.add_argument(
        "--output-dir",
        "--vault",
        dest="output_dir",
        type=Path,
        default=Path("/home/zalmo/documents/obsidian/Videos/Videos"),
        help=(
            "rescript project root "
            "(default: /home/zalmo/documents/obsidian/Videos/Videos)"
        ),
    )
    parser.add_argument(
        "--creative-direction",
        type=Path,
        metavar="FILE",
        help="shared visual standards (default: OUTPUT_DIR/Globals/creative-direction.md)",
    )
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        default=Path("/home/zalmo/transcripts"),
        help="ytstt output root (default: /home/zalmo/transcripts)",
    )
    parser.add_argument(
        "--ytstt",
        type=Path,
        default=Path("/home/zalmo/.local/bin/ytstt"),
        help="ytstt executable",
    )
    harness = parser.add_mutually_exclusive_group()
    harness.add_argument(
        "--codex",
        type=Path,
        default=None,
        help="Codex CLI executable (default: resolve from PATH)",
    )
    harness.add_argument("--opencode", action="store_true",
                         help="use OpenCode for all agent stages with its configured defaults")
    parser.add_argument("--opencode-bin", type=Path, metavar="FILE",
                        help="OpenCode executable override (requires --opencode; default: PATH)")
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument(
        "--cookies-from-browser",
        default=os.environ.get("OBSCRIPT_COOKIES_FROM_BROWSER") or "firefox",
        metavar="BROWSER[:PROFILE]",
        help="use browser cookies for every ytstt request (default: firefox)",
    )
    auth.add_argument(
        "--cookies", type=Path, metavar="FILE",
        help="use an exported Netscape cookies file instead of browser cookies",
    )
    parser.add_argument("--model", help="selected harness model override; default uses harness config")
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high", "xhigh"],
        default="medium",
        help="Codex reasoning effort per stage (default: medium; OpenCode uses its own config)",
    )
    parser.add_argument(
        "--review-passes",
        type=int,
        default=2,
        help="maximum review passes including the first (default: 2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the execution stages without transcribing or invoking an agent",
    )
    phase = parser.add_mutually_exclusive_group()
    phase.add_argument(
        "--storybook", action="store_true",
        help="continue through storybook validation, without rendering",
    )
    phase.add_argument(
        "--render", action="store_true",
        help="render silent animations through the installed HyperFrames skill",
    )
    phase.add_argument(
        "--post-production", action="store_true",
        help="polish an existing project's completed render with effects and varied transitions",
    )
    parser.add_argument(
        "--render-batch-size",
        type=int,
        metavar="SCENES",
        help="maximum scenes per render iteration (default: 20; requires --render)",
    )
    parser.add_argument(
        "--post-production-batch-size",
        type=int,
        metavar="SCENES",
        help="maximum scenes per post-production iteration (default: 20; requires --post-production)",
    )
    parser.add_argument("--verbose", action="store_true", help="show agent CLI output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _resolve_codex(requested: Path | None) -> Path:
    if requested:
        return requested.expanduser().resolve()
    found = shutil.which("codex")
    if not found:
        raise ContractError("Codex CLI was not found in PATH; pass --codex")
    return Path(found).resolve()


def _resolve_opencode(requested: Path | None, *, resume: bool = False) -> Path:
    if requested:
        return requested.expanduser().resolve()
    found = shutil.which("opencode")
    if not found and not resume:
        raise ContractError("OpenCode CLI was not found in PATH; install OpenCode or pass --opencode-bin")
    return Path(found).resolve() if found else Path("opencode")


def _print_dry_run(spec, project_root: Path | None = None) -> None:
    if spec.post_production:
        print(f"resume project: {spec.project_id} ({project_root})")
        print("pipeline: validate-production → post-production → verify-post-production")
        print("requires a completed render; preserves the original video and upstream inputs")
        return
    stages = ["ytstt/source import", "analyze-source"]
    if spec.pipeline != "single":
        stages.append(spec.pipeline)
    if spec.time_controller != "normal":
        stages.append(spec.time_controller)
    if spec.format != "source":
        stages.append(spec.format)
    stages.extend(["plan-script", "write-script", "review-script"])
    if spec.storybook or spec.render:
        stages.extend(["storybook", "validate-storybook"])
    if spec.render:
        stages.extend(["produce-video", "package-production"])
    if project_root:
        print(f"resume project: {spec.project_id} ({project_root})")
        print("completed checkpoints will be reused; saved storybooks will be revalidated")
    print("pipeline: " + " → ".join(stages))
    print(f"sources: {len(spec.sources)}")
    print(f"target_duration_seconds: {spec.target_duration_seconds or 'automatic'}")
    if spec.split_count:
        print(f"split_count: {spec.split_count}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.opencode_bin and not args.opencode:
            raise ContractError("--opencode-bin requires --opencode")
        if args.render_batch_size is not None and not args.render:
            raise ContractError("--render-batch-size requires --render")
        if args.render_batch_size is not None and args.render_batch_size < 1:
            raise ContractError("--render-batch-size must be at least 1")
        if args.post_production_batch_size is not None and not args.post_production:
            raise ContractError("--post-production-batch-size requires --post-production")
        if args.post_production_batch_size is not None and args.post_production_batch_size < 1:
            raise ContractError("--post-production-batch-size must be at least 1")
        if args.command[0] == "new":
            return _new_project(args)
        if args.format is not None:
            raise ContractError("--format is only valid with new; use a positional format modifier for source runs")
        project_root = find_project(args.output_dir.expanduser(), args.command[0]) if len(args.command) == 1 else None
        if project_root:
            if args.project or args.target_duration or args.into is not None:
                raise ContractError("Resuming a project retains its name, duration, and split settings; omit --project, --target-duration, and --into")
            spec = resume_spec(project_root, storybook=args.storybook, render=args.render,
                               post_production=args.post_production)
            if args.creative_direction is None:
                args.creative_direction = Path(read_json(project_root / "project.json")["creative_direction"])
        else:
            if args.post_production:
                raise ContractError("--post-production requires an existing project ID; render the project with --render first")
            spec = parse_command_tokens(
                args.command,
                target_duration=args.target_duration,
                split_count=args.into,
                render=args.render,
                storybook=args.storybook,
            )
        if args.review_passes < 1:
            raise ContractError("--review-passes must be at least 1")
        if args.dry_run:
            _print_dry_run(spec, project_root)
            if spec.render:
                print(f"render_batch_size: {args.render_batch_size or 20}")
            if spec.post_production:
                print(f"post_production_batch_size: {args.post_production_batch_size or 20}")
            print(f"agent: {'OpenCode CLI' if args.opencode else 'Codex CLI'}")
            return 0

        repo_root = Path(__file__).resolve().parents[2]
        opencode = None
        if args.opencode:
            opencode = _resolve_opencode(args.opencode_bin, resume=bool(project_root))
            codex = Path("codex")
        elif project_root:
            codex = (args.codex.expanduser().resolve() if args.codex else
                     Path(shutil.which("codex") or "codex"))
        else:
            codex = _resolve_codex(args.codex)
        args.output_dir.expanduser().mkdir(parents=True, exist_ok=True)
        args.transcripts_dir.expanduser().mkdir(parents=True, exist_ok=True)
        config = RuntimeConfig(
            repo_root=repo_root,
            output_dir=args.output_dir.expanduser().resolve(),
            transcripts_dir=args.transcripts_dir.expanduser().resolve(),
            ytstt=args.ytstt.expanduser().resolve(),
            codex=codex,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            review_passes=args.review_passes,
            project_name=args.project,
            verbose=args.verbose,
            cookies_from_browser=args.cookies_from_browser if not args.cookies else None,
            cookies=args.cookies.expanduser().resolve() if args.cookies else None,
            creative_direction=args.creative_direction,
            harness="opencode" if args.opencode else "codex",
            opencode=opencode,
            render_batch_size=args.render_batch_size or 20,
            post_production_batch_size=args.post_production_batch_size or 20,
        )
        result = Pipeline(config).run(spec)
    except (ContractError, TranscriptionError, AgentError, ProductionError, OSError) as exc:
        print(f"obscript: {exc}", file=sys.stderr)
        return 1

    print(f"[obscript] projeto: {result.project_root}")
    for output in result.outputs:
        print(f"[obscript] artefato: {output}")
    if not result.passed_review:
        print(
            "[obscript] aviso: o roteiro foi salvo, mas ainda requer revisão; consulte review.yaml",
            file=sys.stderr,
        )
        return 2
    print("[obscript] revisão aprovada")
    return 0


def _new_project(args: argparse.Namespace) -> int:
    if args.into is not None or args.storybook or args.render or args.post_production:
        raise ContractError("new creates a manual draft; --into, --storybook, --render, and --post-production are not supported")
    title = " ".join(" ".join(args.command[1:]).split()) if len(args.command) > 1 else args.project or "Novo roteiro"
    if not title.strip():
        raise ContractError("the script title must not be empty")
    spec = CommandSpec(pipeline="single", time_controller="normal", format=args.format or "topics",
                       sources=(), target_duration_seconds=parse_duration(args.target_duration) if args.target_duration else 600)
    if args.dry_run:
        print("pipeline: create-original-project → script-template")
        print(f"title: {title}")
        print(f"format: {spec.format}")
        print(f"target_duration_seconds: {spec.target_duration_seconds}")
        return 0
    output_dir = args.output_dir.expanduser().resolve()
    direction_path = (args.creative_direction or output_dir / "Globals/creative-direction.md").expanduser().resolve()
    root = create_original_project(output_dir, title, spec, direction_path, project_name=args.project)
    print(f"[obscript] project ID: {read_json(root / 'project.json')['id']}")
    print(f"[obscript] projeto: {root}")
    print(f"[obscript] artefato: {root / 'script.md'}")
    print("[obscript] rascunho original criado; escreva seu roteiro em script.md")
    return 0
