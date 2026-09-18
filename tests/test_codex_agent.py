from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from obscript.codex_agent import CodexAgent


class CodexAgentTests(unittest.TestCase):
    def test_storybook_language_exception_is_scoped_to_visual_planning(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = CodexAgent(
                executable=Path("codex"), repo_root=Path(__file__).resolve().parents[1],
                project_root=Path(directory), model=None, reasoning_effort="medium", verbose=False,
            )

            def execute(command, **kwargs):
                output = Path(command[command.index("--output-last-message") + 1])
                output.write_text('{}', encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("obscript.codex_agent.subprocess.run", side_effect=execute) as run:
                agent.run(stage="storybook-01", skill="storybook", schema="storybook", prompt="Plan scenes.")
                visual_prompt = run.call_args.kwargs["input"]
                self.assertIn("instructions in English", visual_prompt)
                self.assertIn("Preserve voiceover.text verbatim", visual_prompt)
                self.assertIn("on-screen text in the script's language", visual_prompt)
                self.assertNotIn("All natural-language fields must be written in Brazilian Portuguese", visual_prompt)

                agent.run(stage="write-script", skill="write-script", schema="script", prompt="Write narration.")
                script_prompt = run.call_args.kwargs["input"]
                self.assertIn("All natural-language fields must be written in Brazilian Portuguese", script_prompt)
                self.assertNotIn("instructions in English", script_prompt)
