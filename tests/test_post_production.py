from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from obscript.post_production import PostProductionAgent
from obscript.production import ProductionError, invalidate_downstream
from obscript.storage import creative_direction_reference, file_sha256, read_json, read_yaml, write_json, write_yaml
from test_visual_production import config_fixture, direction_fixture, script_fixture, story_fixture


class PostProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = config_fixture(self.root)
        self.agent = PostProductionAgent(self.config, self.root)
        self.direction = self.config.creative_direction_path
        self.direction.parent.mkdir(parents=True)
        self.direction.write_text(direction_fixture())
        self.editable = self.root / "production/hyperframes/index.html"
        self.editable.parent.mkdir(parents=True)
        self.editable.write_text("original editable composition")
        for name, value in [("approved-script", script_fixture()), ("review", {"verdict": "pass"}),
                            ("knowledge", {}), ("plan", {})]:
            write_json(self.root / ".obscript" / f"{name}.json", value)
        write_json(self.root / ".obscript/approved-inputs.json", {
            "files": {name: file_sha256(self.root / ".obscript" / name)
                      for name in ["approved-script.json", "review.json", "knowledge.json", "plan.json"]},
        })
        write_json(self.root / ".obscript/creative-direction-source.json",
                   creative_direction_reference(self.direction, direction_fixture()))
        write_yaml(self.root / "storybook.yaml", story_fixture())
        write_yaml(self.root / "production.yaml", {"status": "complete"})
        (self.root / "video.mp4").write_bytes(b"original video")
        self.write_render_receipt()
        for scene in story_fixture()["scenes"]:
            scene_dir = self.root / "production/scenes" / scene["id"]
            scene_dir.mkdir(parents=True)
            (scene_dir / "scene.mp4").write_bytes(b"original scene")
            write_json(scene_dir / "manifest.json", {
                "scene_id": scene["id"], "script_section_id": scene["script_section_id"],
                "generator": "hyperframes", "status": "complete", "estimated_duration_seconds": 3,
                "actual_duration_seconds": 3, "output_files": ["scene.mp4"],
            })
        self.calls = []
        self.duration = 12
        self.failure = False
        self.mutate = None
        self.omit_report = False
        self.addCleanup(patch.stopall)
        patch("obscript.post_production.shutil.which", return_value="ffprobe").start()
        patch("obscript.production.probe_media", return_value=3).start()
        patch("obscript.post_production.probe_media", side_effect=self.probe).start()
        patch.object(self.agent, "_execute", side_effect=self.execute).start()

    def write_render_receipt(self):
        paths = [self.root / ".obscript/approved-script.json", self.root / ".obscript/review.json",
                 self.direction, self.root / "storybook.yaml"]
        write_json(self.root / ".obscript/production-inputs.json", {
            "inputs": {str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path):
                       file_sha256(path) for path in paths},
            "video_sha256": file_sha256(self.root / "video.mp4"),
        })

    def probe(self, path):
        return 12 if path.name == "video.mp4" else self.duration

    def execute(self, stage, request_path, output_dir):
        self.calls.append(stage)
        request = read_json(request_path)
        self.assertEqual(request["operation"], "post-production")
        self.assertEqual(request["storybook"], story_fixture())
        self.assertEqual(request["audio_policy"], "none")
        self.assertFalse(request["hyperframes"]["render"]["audio"])
        self.assertEqual(Path(request["hyperframes"]["project_directory"]), output_dir / "hyperframes")
        (output_dir / "hyperframes/index.html").write_text("polished editable composition")
        if self.mutate:
            self.mutate.write_text("modified upstream")
        if self.failure:
            raise ProductionError("synthetic executor failure")
        Path(request["output_video"]).write_bytes(b"polished video")
        if not self.omit_report:
            Path(request["report"]).write_text("scene-001: improved vignette; checked readable labels.")

    def test_polish_preserves_original_and_skips_verified_completion(self):
        original = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result = self.agent.polish()
        self.assertEqual(result, self.root / "video-polished.mp4")
        self.assertEqual(result.read_bytes(), b"polished video")
        for path, data in original.items():
            self.assertEqual(path.read_bytes(), data, str(path))
        manifest = read_yaml(self.root / "post-production.yaml")
        self.assertEqual(manifest["status"], "complete")
        self.assertFalse(manifest["audio"])
        self.assertEqual(manifest["actual_duration_seconds"], 12)
        self.assertEqual(self.agent.polish(), result)
        self.assertEqual(self.calls, ["post-production"])

    def test_stale_render_inputs_block_executor(self):
        for path in [self.root / "storybook.yaml", self.direction, self.root / "video.mp4",
                     self.root / ".obscript/approved-script.json"]:
            with self.subTest(path=path):
                original = path.read_bytes()
                if path.name == "storybook.yaml":
                    story = story_fixture()
                    story["scenes"][0]["render_brief"] = "new plan"
                    write_yaml(path, story)
                elif path.name == "approved-script.json":
                    script = script_fixture()
                    script["thesis"] = "Changed thesis"
                    write_json(path, script)
                else:
                    path.write_bytes(b"changed")
                with self.assertRaises(ProductionError):
                    self.agent.polish()
                path.write_bytes(original)
        self.assertFalse(self.calls)

    def test_duration_drift_and_audio_failure_prevent_publication(self):
        self.duration = 11
        with self.assertRaisesRegex(ProductionError, "duration differs"):
            self.agent.polish()
        self.assert_failed_with_original_preserved()
        def reject_audio(path):
            if path.name == "video.mp4":
                return 12
            raise ProductionError("audio track")
        with patch("obscript.post_production.probe_media", side_effect=reject_audio):
            with self.assertRaisesRegex(ProductionError, "audio track"):
                self.agent.polish()
        self.assert_failed_with_original_preserved()

    def assert_failed_with_original_preserved(self):
        self.assertFalse((self.root / "video-polished.mp4").exists())
        self.assertEqual((self.root / "video.mp4").read_bytes(), b"original video")
        manifest = read_yaml(self.root / "post-production.yaml")
        self.assertEqual(manifest["status"], "failed")
        self.assertIsNone(manifest["final_video"])

    def test_executor_failure_resumes_copied_project(self):
        self.failure = True
        with self.assertRaisesRegex(ProductionError, "synthetic executor failure"):
            self.agent.polish()
        self.assert_failed_with_original_preserved()
        copied = self.root / "post-production/hyperframes/custom.txt"
        copied.write_text("partial editable work")
        self.failure = False
        self.agent.polish()
        self.assertEqual(copied.read_text(), "partial editable work")
        self.assertEqual(self.calls, ["post-production", "post-production"])

    def test_mutated_upstream_is_restored_and_blocks_publication(self):
        self.mutate = self.root / ".obscript/approved-script.json"
        original = self.mutate.read_bytes()
        with self.assertRaisesRegex(ProductionError, "immutable source inputs"):
            self.agent.polish()
        self.assertEqual(self.mutate.read_bytes(), original)
        self.assert_failed_with_original_preserved()

    def test_missing_report_blocks_publication(self):
        self.omit_report = True
        with self.assertRaisesRegex(ProductionError, "report"):
            self.agent.polish()
        self.assert_failed_with_original_preserved()

    def test_changed_source_archives_old_polish_and_rebuilds_copy(self):
        self.agent.polish()
        self.editable.write_text("revised source composition")
        self.agent.polish()
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(list((self.root / ".obscript/invalidated").rglob("video-polished.mp4")))
        self.assertEqual(self.editable.read_text(), "revised source composition")

    def test_retry_does_not_accept_stale_report(self):
        self.duration = 11
        with self.assertRaises(ProductionError):
            self.agent.polish()
        self.duration = 12
        self.omit_report = True
        with self.assertRaisesRegex(ProductionError, "report"):
            self.agent.polish()
        self.assert_failed_with_original_preserved()

    def test_changed_shared_direction_is_preserved_after_executor_failure(self):
        self.mutate = self.direction
        self.failure = True
        with self.assertRaisesRegex(ProductionError, "immutable source inputs"):
            self.agent.polish()
        self.assertEqual(self.direction.read_text(), "modified upstream")
        self.assert_failed_with_original_preserved()

    def test_source_media_mutation_blocks_publication(self):
        self.mutate = self.root / "production/scenes/scene-001/scene.mp4"
        with self.assertRaisesRegex(ProductionError, "immutable source inputs"):
            self.agent.polish()
        self.assert_failed_with_original_preserved()

    def test_tampered_polished_video_is_not_reused(self):
        self.agent.polish()
        (self.root / "video-polished.mp4").write_bytes(b"tampered")
        self.agent.polish()
        self.assertEqual(self.calls, ["post-production", "post-production"])
        self.assertEqual((self.root / "video-polished.mp4").read_bytes(), b"polished video")

    def test_upstream_invalidation_archives_polished_outputs(self):
        self.agent.polish()
        invalidate_downstream(self.root, "storybook")
        for name in ["production", "video.mp4", "post-production", "video-polished.mp4", "post-production.yaml",
                     ".obscript/post-production-inputs.json", ".obscript/post-production-attempt-inputs.json"]:
            self.assertFalse((self.root / name).exists(), name)
        self.assertTrue(list((self.root / ".obscript/invalidated").rglob("video-polished.mp4")))
