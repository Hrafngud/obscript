from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from obscript.codex_agent import CodexAgent
from obscript.storage import read_json


class CodexAgentTests(unittest.TestCase):
    def test_reviewer_enables_live_search_only_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = CodexAgent(executable=Path("codex"), repo_root=Path(__file__).resolve().parents[1],
                               project_root=Path(directory), model="chosen-model", reasoning_effort="low", verbose=False)
            def execute(command, **kwargs):
                Path(command[command.index("--output-last-message") + 1]).write_text('{}')
                return subprocess.CompletedProcess(command, 0, "", "")
            with patch("obscript.codex_agent.subprocess.run", side_effect=execute) as run:
                agent.run(stage="review-storybook-01", skill="review-storybook", schema="storybook-review",
                          prompt="Review the scenes.", web_search=True)
                command = run.call_args.args[0]
                self.assertEqual(command[:3], ["codex", "--search", "exec"])
                self.assertIn('model_reasoning_effort="low"', command)
                self.assertEqual(command[command.index("--model") + 1], "chosen-model")
                self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
                agent.run(stage="recheck-storybook-01", skill="review-storybook", schema="storybook-review", prompt="Recheck.")
                self.assertNotIn("--search", run.call_args.args[0])

    def test_targeted_repair_schema_uses_the_complete_scene_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(__file__).resolve().parents[1]
            agent = CodexAgent(executable=Path("codex"), repo_root=repo, project_root=Path(directory),
                               model=None, reasoning_effort="medium", verbose=False)
            schema = read_json(agent._resolved_schema("storybook-revision"))
            original = read_json(repo / "schemas/storybook.schema.json")
            scene = schema["properties"]["scenes"]["items"]
            original_scene = original["properties"]["scenes"]["items"]
            self.assertEqual(scene["properties"], original_scene["properties"])
            self.assertEqual(set(scene["required"]), set(original_scene["required"]) | {"external_graphics"})

    def test_all_codex_output_schemas_require_every_property_recursively(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(__file__).resolve().parents[1]
            agent = CodexAgent(executable=Path("codex"), repo_root=repo, project_root=Path(directory),
                               model=None, reasoning_effort="high", verbose=False)

            def check(node):
                if isinstance(node, dict):
                    if node.get("type") == "object":
                        self.assertEqual(set(node["required"]), set(node["properties"]))
                        self.assertIs(node["additionalProperties"], False)
                    for child in node.values():
                        check(child)
                elif isinstance(node, list):
                    for child in node:
                        check(child)

            for source in (repo / "schemas").glob("*.schema.json"):
                name = source.name.removesuffix(".schema.json")
                with self.subTest(schema=name):
                    before = source.read_bytes()
                    resolved = agent._resolved_schema(name)
                    self.assertTrue(resolved.is_relative_to(agent.state_dir))
                    check(read_json(resolved))
                    self.assertEqual(source.read_bytes(), before)
            source_scene = read_json(repo / "schemas/storybook.schema.json")["properties"]["scenes"]["items"]
            self.assertNotIn("external_graphics", source_scene["required"])

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
