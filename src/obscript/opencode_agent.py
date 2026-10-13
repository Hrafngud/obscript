from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .agent import AgentError, StructuredAgent
from .contracts import ContractError
from .schema_validation import validate_structure
from .storage import read_json, write_json


class OpenCodeHarness:
    """Translate obscript requests to the native, noninteractive OpenCode CLI."""

    def __init__(self, executable: Path, repo_root: Path, model: str | None = None) -> None:
        self.executable = executable
        self.repo_root = repo_root
        self.model = model

    def command(self) -> list[str]:
        # V2 uses the process directory. Its private server must inherit this
        # stage's inline skills and permissions instead of a service's old env.
        command = [str(self.executable), "run", "--format", "json", "--standalone"]
        if self.model:
            command.extend(["--model", self.model])
        return command

    def environment(self, *, directory: Path | None = None, output_dir: Path | None = None) -> dict[str, str]:
        env = os.environ.copy()
        # OpenCode resolves its location from PWD before falling back to cwd.
        if directory is not None:
            env["PWD"] = str(directory.resolve())
        try:
            config = json.loads(env.get("OPENCODE_CONFIG_CONTENT") or "{}")
        except json.JSONDecodeError as exc:
            raise AgentError("OPENCODE_CONFIG_CONTENT must contain a JSON object") from exc
        if not isinstance(config, dict):
            raise AgentError("OPENCODE_CONFIG_CONTENT must contain a JSON object")
        skills = config.setdefault("skills", {})
        if not isinstance(skills, dict) or not isinstance(skills.get("paths", []), list):
            raise AgentError("OpenCode skills configuration must contain a paths list")
        if any(not isinstance(path, str) for path in skills.get("paths", [])):
            raise AgentError("OpenCode skill paths must be strings")
        # Keep existing Codex-installed skills available when switching harnesses.
        paths = [str(self.repo_root / "skills"), str(Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser() / "skills")]
        skills["paths"] = list(dict.fromkeys([*skills.get("paths", []), *paths]))
        if output_dir is None:
            config["permission"] = {
                "*": "deny", "read": "allow", "glob": "allow", "grep": "allow",
                "external_directory": "allow",
            }
        else:
            permission = config.get("permission", {})
            if isinstance(permission, str):
                permission = {"*": permission}
            if not isinstance(permission, dict):
                raise AgentError("OpenCode permission configuration must be an object or string")
            config["permission"] = {
                **permission,
                "edit": {"*": "deny", str(output_dir.resolve() / "**"): "allow"},
                "bash": "allow", "read": "allow", "glob": "allow", "grep": "allow",
                "skill": "allow", "external_directory": "allow",
                "task": "deny", "question": "deny",
            }
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
        return env

    @staticmethod
    def error_detail(stdout: str) -> str | None:
        """Extract a provider failure without including raw response bodies."""
        detail = None
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("type") != "error":
                continue
            error = event.get("error")
            if not isinstance(error, dict):
                detail = str(error or "Unknown OpenCode error")
                continue
            data = error.get("data")
            data = data if isinstance(data, dict) else {}
            message = error.get("message") or data.get("message") or "Unknown OpenCode error"
            kind = error.get("type") or error.get("name")
            status = error.get("status") or data.get("statusCode")
            prefix = " ".join(str(value) for value in [kind, f"(HTTP {status})" if status else None] if value)
            detail = f"{prefix}: {message}" if prefix else str(message)
        return detail

    @staticmethod
    def response(stdout: str) -> str:
        messages: dict[str, dict[str, str]] = {}
        for line in stdout.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AgentError("OpenCode returned an invalid JSON event stream") from exc
            if not isinstance(event, dict):
                raise AgentError("OpenCode returned a non-object event")
            if event.get("type") == "error":
                raise AgentError(f"OpenCode reported an error: {OpenCodeHarness.error_detail(line)}")
            if event.get("type") != "text":
                continue
            part = event.get("part", {})
            if not isinstance(part, dict) or not isinstance(part.get("text"), str):
                raise AgentError("OpenCode returned an invalid text event")
            message_id = part.get("messageID", "response")
            part_id = part.get("id")
            if not isinstance(message_id, str) or (part_id is not None and not isinstance(part_id, str)):
                raise AgentError("OpenCode returned invalid text identifiers")
            parts = messages.setdefault(message_id, {})
            parts[part_id or str(len(parts))] = part["text"]
        if not messages:
            raise AgentError("OpenCode produced no assistant response")
        return "\n".join(next(reversed(messages.values())).values()).strip()


class OpenCodeAgent(StructuredAgent):
    def _execute(self, *, stage: str, prompt: str, schema_path: Path, output_path: Path) -> None:
        harness = OpenCodeHarness(self.executable, self.repo_root, self.model)
        schema = read_json(schema_path)
        prompt += "\nOutput JSON Schema:\n" + json.dumps(schema, ensure_ascii=False)
        log_path = output_path.with_suffix(".executor.log")
        print(f"[obscript] opencode → {stage}", flush=True)
        try:
            result = subprocess.run(harness.command(), cwd=self.project_root, input=prompt, text=True,
                                    capture_output=True, check=False,
                                    env=harness.environment(directory=self.project_root))
        except OSError as exc:
            raise AgentError(f"OpenCode executor could not start: {exc}") from exc
        log = (result.stdout or "") + (result.stderr or "")
        log_path.write_text(log, encoding="utf-8")
        if self.verbose:
            print(log, flush=True)
        if result.returncode:
            error = harness.error_detail(result.stdout or "")
            detail = f": {error[:500]}" if error else ""
            raise AgentError(f"OpenCode failed during {stage} (exit {result.returncode}){detail}; see {log_path}")
        try:
            response = harness.response(result.stdout or "")
            output_path.with_suffix(".response.txt").write_text(response, encoding="utf-8")
            if response.startswith("```") and response.endswith("```"):
                response = response.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(response)
            validate_structure(data, schema)
        except (AgentError, ContractError, json.JSONDecodeError, IndexError) as exc:
            raise AgentError(f"OpenCode returned invalid structured output during {stage}: {exc}; see {log_path}") from exc
        write_json(output_path, data)
