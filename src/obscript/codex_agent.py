from __future__ import annotations

import subprocess
from pathlib import Path

from .agent import AgentError, StructuredAgent

# Retained for callers using the original Codex adapter.
CodexError = AgentError


class CodexAgent(StructuredAgent):
    def _execute(self, *, stage: str, prompt: str, schema_path: Path, output_path: Path) -> None:
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
        if self.model:
            command.extend(["--model", self.model])
        command.extend(["--config", f'model_reasoning_effort="{self.reasoning_effort}"'])
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
