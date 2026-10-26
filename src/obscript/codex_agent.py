from __future__ import annotations

import subprocess
from pathlib import Path

from .agent import AgentError, StructuredAgent
from .storage import read_json, write_json

# Retained for callers using the original Codex adapter.
CodexError = AgentError


class CodexAgent(StructuredAgent):
    def _resolved_schema(self, schema_name: str) -> Path:
        source = super()._resolved_schema(schema_name)
        schema = read_json(source)

        def require_properties(node):
            if isinstance(node, dict):
                # Codex strict output requires all object properties, including
                # fields that remain optional when reading older saved artifacts.
                if node.get("type") == "object":
                    node["required"] = list(node.get("properties", {}))
                for child in node.values():
                    require_properties(child)
            elif isinstance(node, list):
                for child in node:
                    require_properties(child)

        require_properties(schema)
        destination = self.state_dir / f"{schema_name}.codex.schema.json"
        write_json(destination, schema)
        return destination

    def _execute(self, *, stage: str, prompt: str, schema_path: Path, output_path: Path,
                 image_paths: tuple[Path, ...] = (), web_search: bool = False) -> None:
        command = [
            str(self.executable),
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--color",
            "never",
            "-C",
            str(self.project_root),
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
        ]
        if web_search:
            command.insert(1, "--search")
        if self.model:
            command.extend(["--model", self.model])
        command.extend(["--config", f'model_reasoning_effort="{self.reasoning_effort}"'])
        for path in image_paths:
            command.extend(["--image", str(path)])
        command.append("-")

        print(f"[obscript] codex → {stage}", flush=True)
        try:
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                stdout=None if self.verbose else subprocess.PIPE,
                stderr=None if self.verbose else subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError as exc:
            raise CodexError(f"Codex executable not found: {self.executable}") from exc
        if completed.returncode != 0:
            details = ""
            if not self.verbose:
                details = (completed.stderr or completed.stdout or "").strip()
            suffix = f": {details}" if details else ""
            raise CodexError(f"Codex failed during {stage} (exit {completed.returncode}){suffix}")
