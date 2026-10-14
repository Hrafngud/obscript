from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from obscript.cli import main
from obscript.contracts import ContractError
from obscript.models import CommandSpec
from obscript.original import import_original_script, original_context, parse_original_script, script_signature
from obscript.pipeline import Pipeline
from obscript.projects import create_original_project, resume_spec
from obscript.schema_validation import validate_structure
from obscript.storage import read_json, read_yaml, render_script, write_json, write_yaml
from test_visual_production import REPO, config_fixture, direction_fixture, scene_fixture, script_fixture


class OriginalProjectsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = config_fixture(self.base)
        direction = self.config.creative_direction_path
        direction.parent.mkdir(parents=True)
        direction.write_text(direction_fixture())
        self.spec = CommandSpec("single", "normal", "source", (), target_duration_seconds=12)
        self.root = create_original_project(self.config.output_dir, "Original", self.spec, direction)
        self.draft = render_script(script_fixture())
        (self.root / "script.md").write_text(self.draft)
        self.calls = []
        self.verdict = "pass"
        self.mutate = None
        self.prompts = []
        self.addCleanup(patch.stopall)
        patch("sys.stdout", new=io.StringIO()).start()
        self.ingest = patch("obscript.pipeline.ingest_source").start()
        self.agent = patch("obscript.pipeline.Pipeline._agent").start().return_value
        self.agent.run.side_effect = self.agent_run
        self.producer = patch("obscript.pipeline.ProductionAgent").start()
        self.producer.return_value.produce.side_effect = self.produce

    def agent_run(self, *, stage, skill, prompt, schema):
        self.calls.append(skill)
        self.prompts.append(prompt)
        if skill == "review-script":
            value = {"schema_version": "1", "verdict": self.verdict,
                     "duration": {"expected_seconds": 12, "estimated_seconds": 12, "status": "on_target"},
                     "coverage": {"status": "complete", "missing_topic_refs": []}, "issues": [],
                     "recommendation": {"rerun": [], "reason": "Revisão"}}
        elif skill == "storybook":
            script = read_json(self.root / ".obscript/approved-script.json")
            target = script["metadata"]["target_duration_seconds"]
            scenes = [scene_fixture(i + 1, s["id"], s["narration"]) for i, s in enumerate(script["sections"])]
            for i, scene in enumerate(scenes):
                start, end = target * i // len(scenes), target * (i + 1) // len(scenes)
                scene["timing"] = {"estimated_start_seconds": start, "estimated_end_seconds": end}
                scene["voiceover"]["estimated_seconds"] = end - start
            value = {"schema_version": "3", "target_duration_seconds": target, "scenes": scenes}
        else:
            self.fail(f"Original projects must not invoke {skill}")
        if self.mutate:
            self.mutate(skill)
        path = self.root / ".obscript" / f"test-{stage}.json"
        write_json(path, value)
        return value, path

    def produce(self, **kwargs):
        (self.root / "video.mp4").write_bytes(b"video fixture")
        write_yaml(self.root / "production.yaml", {"status": "complete"})
        return self.root / "video.mp4"

    def run_project(self, **flags):
        return Pipeline(self.config).run(resume_spec(self.root, storybook=flags.pop("storybook", False),
                                                    render=flags.pop("render", False), **flags))

    def test_import_preserves_narration_and_generates_schema_valid_context(self):
        parsed = parse_original_script(self.root / "script.md", self.spec)
        self.assertEqual([s["narration"] for s in parsed["sections"]],
                         [s["narration"] for s in script_fixture()["sections"]])
        knowledge, plan = original_context(parsed, self.root)
        for schema, value in [("script", parsed), ("knowledge", knowledge), ("plan", plan)]:
            validate_structure(value, read_json(REPO / "schemas" / f"{schema}.schema.json"))
        self.assertEqual(sum(s["estimated_seconds"] for s in parsed["sections"]), 12)

    def test_storybook_uses_shared_file_layout_and_reuses_review(self):
        result = self.run_project(storybook=True)
        self.assertTrue(result.passed_review)
        self.assertEqual(self.calls, ["review-script", "storybook"])
        self.ingest.assert_not_called()
        self.assertIn("### scene-001", (self.root / "script.md").read_text())
        self.assertNotIn("### scene-001", (self.root / "script-readable.md").read_text())
        self.assertFalse((self.root / "script-timed.md").exists())
        approved = read_json(self.root / ".obscript/approved-script.json")
        parsed, _ = import_original_script(self.root, self.spec)
        self.assertEqual(parsed, approved)
        self.calls.clear()
        self.run_project(storybook=True)
        self.assertEqual(self.calls, [])
        self.assertEqual(read_json(self.root / "project.json")["origin"], "original")

    def test_scene_cues_round_trip_paragraphs_and_inline_annotations(self):
        script = script_fixture()
        script["sections"][0]["narration"] = "Você *observa* o padrão.\n\nAgora veja a **causa**."
        (self.root / "script.md").write_text(render_script(script))
        imported = parse_original_script(self.root / "script.md", self.spec)
        write_json(self.root / ".obscript/approved-script.json", imported)
        scenes = [
            scene_fixture(1, imported["sections"][0]["id"], "Você *observa* o padrão."),
            scene_fixture(2, imported["sections"][0]["id"], "Agora veja a **causa**."),
            scene_fixture(3, imported["sections"][1]["id"], imported["sections"][1]["narration"]),
            scene_fixture(4, imported["sections"][2]["id"], imported["sections"][2]["narration"]),
        ]
        (self.root / "script.md").write_text(render_script(imported, {"scenes": scenes}))
        reparsed = parse_original_script(self.root / "script.md", self.spec)
        self.assertEqual(script_signature(reparsed), script_signature(imported))
        selected, _ = import_original_script(self.root, self.spec)
        self.assertEqual(selected["sections"][0]["narration"], script["sections"][0]["narration"])

    def test_render_directly_and_resume_without_duplicate_model_calls(self):
        self.run_project(render=True)
        self.assertEqual(self.calls, ["review-script", "storybook"])
        self.producer.return_value.produce.assert_called_once()
        self.calls.clear()
        self.run_project(render=True)
        self.assertEqual(self.calls, [])
        self.producer.return_value.produce.assert_called_once()

    def test_review_only_then_storybook(self):
        self.run_project()
        self.assertEqual(self.calls, ["review-script"])
        self.assertFalse((self.root / "storybook.yaml").exists())
        self.run_project(storybook=True)
        self.assertEqual(self.calls, ["review-script", "storybook"])

    def test_edits_in_either_view_reapprove_and_archive_old_render(self):
        for filename in ["script.md", "script-readable.md"]:
            with self.subTest(filename=filename):
                self.run_project(render=True)
                path = self.root / filename
                path.write_text(path.read_text().replace("A causa explica", "O mecanismo explica"))
                self.calls.clear()
                self.run_project(storybook=True)
                self.assertEqual(self.calls, ["review-script", "storybook"])
                self.assertFalse((self.root / "video.mp4").exists())
                self.assertTrue(list((self.root / ".obscript/invalidated").glob("*/video.mp4")))
                for name in ["script.md", "script-readable.md"]:
                    self.assertIn("O mecanismo explica", (self.root / name).read_text())
                # Reset wording for the second independent edit.
                (self.root / "script.md").write_text(self.draft)
                (self.root / "script-readable.md").write_text(self.draft)

    def test_conflicting_edits_leave_both_views_intact(self):
        self.run_project(storybook=True)
        for filename, replacement in [("script.md", "O mecanismo explica"), ("script-readable.md", "A relação explica")]:
            path = self.root / filename
            path.write_text(path.read_text().replace("A causa explica", replacement))
        before = {name: (self.root / name).read_text() for name in ["script.md", "script-readable.md"]}
        with self.assertRaisesRegex(ContractError, "conflicting narration edits"):
            self.run_project(storybook=True)
        for name, text in before.items():
            self.assertEqual((self.root / name).read_text(), text)

    def test_failed_review_keeps_manual_narration_and_blocks_storybook(self):
        self.verdict = "revise"
        result = self.run_project(render=True)
        self.assertFalse(result.passed_review)
        self.assertEqual(self.calls, ["review-script"])
        self.assertEqual((self.root / "script.md").read_text(), self.draft)
        self.assertFalse((self.root / ".obscript/approved-script.json").exists())
        self.assertEqual(read_json(self.root / "project.json")["status"], "needs_review")
        self.producer.assert_not_called()

    def test_template_is_rejected_before_agent_calls(self):
        template = create_original_project(self.config.output_dir, "Empty", self.spec,
                                           self.config.creative_direction_path)
        with self.assertRaisesRegex(ContractError, "template placeholders"):
            Pipeline(self.config).run(resume_spec(template, storybook=True, render=False))
        self.agent.run.assert_not_called()

    def test_rejected_script_can_be_edited_and_reviewed_again(self):
        self.verdict = "revise"
        self.run_project(storybook=True)
        path = self.root / "script.md"
        path.write_text(path.read_text().replace("A causa explica", "O mecanismo explica"))
        self.verdict = "pass"
        self.calls.clear()
        self.assertTrue(self.run_project(storybook=True).passed_review)
        self.assertEqual(self.calls, ["review-script", "storybook"])
        self.assertIn("O mecanismo explica", (self.root / "script-readable.md").read_text())

    def test_duration_edits_and_notes_trigger_review(self):
        self.run_project(storybook=True)
        path = self.root / "script-readable.md"
        path.write_text(path.read_text().replace("target_duration_seconds: 12", "target_duration_seconds: 18"))
        self.calls.clear()
        self.run_project(storybook=True)
        self.assertEqual(self.calls, ["review-script", "storybook"])
        self.assertEqual(read_yaml(self.root / "storybook.yaml")["target_duration_seconds"], 18)
        (self.root / "fontes.md").write_text("Referências do autor")
        self.calls.clear()
        self.run_project(storybook=True)
        self.assertEqual(self.calls, ["review-script", "storybook"])
        self.assertIn("not independent factual evidence", self.prompts[-2])
        self.assertIn(str(self.root / "fontes.md"), self.prompts[-2])

    def test_changed_narration_blocks_rerender_and_polish(self):
        self.run_project(render=True)
        path = self.root / "script.md"
        path.write_text(path.read_text().replace("A causa explica", "O mecanismo explica"))
        with patch("obscript.pipeline.PostProductionAgent") as polish:
            for flags in [{"rerender_scene_id": "scene-001"}, {"post_production": True}]:
                with self.subTest(flags=flags), self.assertRaisesRegex(ContractError, "changed; run PROJECT_ID"):
                    self.run_project(**flags)
            polish.assert_not_called()
        self.producer.return_value.rerender.assert_not_called()

    def test_checkpoint_tampering_is_not_silently_approved(self):
        self.run_project(storybook=True)
        path = self.root / ".obscript/plan.json"
        plan = read_json(path)
        plan["thesis"] = "Changed behind the review"
        write_json(path, plan)
        with self.assertRaisesRegex(ContractError, "Approved script inputs changed"):
            self.run_project(render=True)

    def test_edits_during_review_or_storybook_are_preserved(self):
        for during in ["review-script", "storybook"]:
            with self.subTest(during=during):
                (self.root / "script.md").write_text(self.draft)
                def mutate(skill):
                    if skill == during:
                        path = self.root / "script.md"
                        path.write_text(path.read_text().replace("A causa explica", "Edição concorrente explica"))
                self.mutate = mutate
                with self.assertRaisesRegex(ContractError, "changed"):
                    self.run_project(storybook=True)
                self.assertIn("Edição concorrente explica", (self.root / "script.md").read_text())

    def test_cli_original_uses_opencode_and_does_not_create_transcripts(self):
        project_id = read_json(self.root / "project.json")["id"]
        transcripts = self.base / "unused-transcripts"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([project_id, "--storybook", "--opencode", "--vault", str(self.config.output_dir),
                                   "--transcripts-dir", str(transcripts)]), 0)
        self.assertFalse(transcripts.exists())
        self.assertEqual(read_yaml(self.root / "run.yaml")["agent"], "OpenCode CLI")


if __name__ == "__main__":
    unittest.main()
