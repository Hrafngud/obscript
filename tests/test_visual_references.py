from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from obscript.agent import AgentError
from obscript.cli import main
from obscript.codex_agent import CodexAgent
from obscript.contracts import ContractError
from obscript.models import VisualReferenceConfig
from obscript.opencode_agent import OpenCodeAgent
from obscript.storage import read_json, read_yaml, write_json
from obscript.visual_references import (
    ASPECTS, ReferenceExtractor, VisualReferenceError, ensure_source_references,
    frame_features, probe_windows, select_segments, transcript_anchors,
    validate_analysis, validate_config, write_reference_collection,
)
from test_visual_production import REPO, config_fixture


def analysis_fixture(segments):
    observations = []
    for s in segments:
        fields = {a: {"status": "unknown", "description": "Evidência insuficiente.", "evidence": []} for a in ASPECTS}
        fields["composition_framing"] = {"status": "observed", "description": "Campo central claro.",
            "evidence": [{"frame_path": s["frames"][0]["path"], "source_seconds": s["frames"][0]["source_seconds"]}]}
        observations.append({"segment_id": s["id"], **fields, "limitations": ["Não é possível identificar a fonte tipográfica."]})
    return {"segments": observations, "consolidated_brief": "Adaptar o foco central observado no segment-01; movimentos permanecem incertos."}


class SelectionTests(unittest.TestCase):
    def test_visual_diversity_beats_uniform_or_consecutive_sampling(self):
        config = VisualReferenceConfig()
        candidates = [{"center": t, "features": [v] * 60, "activity": activity}
                      for t, v, activity in [(10, .1, .8), (40, .1, .8), (78, .9, .3), (133, .5, .2)]]
        selected = select_segments(candidates, 150, config)
        self.assertEqual([s["center"] for s in selected], [10, 78, 133])
        self.assertEqual([s["end_seconds"] - s["start_seconds"] for s in selected], [15] * 3)

    def test_short_source_overlap_and_redundancy(self):
        candidates = [{"center": c, "features": [v] * 60, "activity": .1}
                      for c, v in [(0, .1), (4, .9), (8, .5)]]
        short = select_segments(candidates, 8, VisualReferenceConfig())
        self.assertEqual(len(short), 1)
        self.assertEqual((short[0]["start_seconds"], short[0]["end_seconds"]), (0, 8))
        duplicates = [{"center": c, "features": [.1] * 60, "activity": .1} for c in [10, 40, 70]]
        self.assertEqual(len(select_segments(duplicates, 90, VisualReferenceConfig())), 1)

    def test_probe_budget_uses_pause_chapter_and_broad_coverage(self):
        windows = probe_windows(200, VisualReferenceConfig(probe_count=6), [34, 41, 69], [{"start_time": 19}])
        self.assertLessEqual(len(windows), 6)
        self.assertIn("chapter", [w[2] for w in windows])
        self.assertIn("transcript-pause", [w[2] for w in windows])
        self.assertIn("coverage", [w[2] for w in windows])
        self.assertTrue(all(0 <= a < b <= 200 and b - a <= 4.001 for a, b, _ in windows))

    def test_descriptors_detect_color_spatial_change_and_abrupt_difference(self):
        dark, light = bytes([0] * 432), bytes([255] * 432)
        f1, changes = frame_features(dark * 3 + light * 3)
        f2, _ = frame_features(dark * 6)
        self.assertIn(1., changes)
        self.assertNotEqual(f1, f2)
        with self.assertRaises(VisualReferenceError):
            frame_features(b"")

    def test_transcript_pauses_json_srt_and_malformed_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "transcript.json", {"segments": [{"start": 0, "end": 3}, {"start": 5, "end": 8}, {"start": 9, "end": 10}]})
            self.assertEqual(transcript_anchors(root), [5, 9])
            (root / "transcript.json").write_text("broken")
            (root / "transcript.srt").write_text("1\n00:00:00,000 --> 00:00:03,000\nText\n\n2\n00:00:05,000 --> 00:00:08,000\nText")
            self.assertEqual(transcript_anchors(root), [5])

    def test_config_rejects_unbounded_or_nonfinite_work(self):
        for values in [{"clip_count": 0}, {"frames_per_clip": 1}, {"clip_seconds": float("nan")},
                       {"probe_count": 1000}, {"max_height": 2160}, {"timeout_seconds": float("inf")}]:
            with self.subTest(values=values), self.assertRaises(ContractError):
                validate_config(VisualReferenceConfig(**values))


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        write_json(self.source / "source.json", {"id": "source-01", "source": "https://example.com/video", "title": "Video"})
        self.config = replace(config_fixture(self.root), cookies_from_browser=None)
        self.downloads = []
        self.agent = Mock()
        self.agent.run.side_effect = self.analyze
        self.addCleanup(patch.stopall)
        patch("obscript.visual_references.shutil.which", return_value="tool").start()
        patch.object(ReferenceExtractor, "run", autospec=True, side_effect=self.command).start()
        self.section_mock = patch.object(ReferenceExtractor, "section", autospec=True, side_effect=self.section).start()
        patch.object(ReferenceExtractor, "features", autospec=True, side_effect=self.features).start()
        patch("sys.stdout", new=io.StringIO()).start()

    def command(self, extractor, command, **kwargs):
        if "--dump-single-json" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps({"id": "video-id", "duration": 180, "title": "Video", "formats": []}), "")
        Path(command[-1]).write_bytes(b"frame")
        return subprocess.CompletedProcess(command, 0, "", "")

    def section(self, extractor, url, start, end, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"clip")
        self.downloads.append((start, end, destination))
        return destination

    def features(self, extractor, path):
        number = int(path.stem.split("-")[1])
        return [.12 * number] * 61, [0., .25, .03, .02, .01, .01, .01]

    def analyze(self, **kwargs):
        artifact = read_json(self.source / "visual-references/reference.json")
        return analysis_fixture(artifact["segments"]), self.root / "analysis.json"

    def extract(self):
        return ensure_source_references(self.source, self.config, self.agent)

    def test_artifact_generation_original_timestamps_frames_and_collection(self):
        path = self.extract()
        value = read_json(path)
        self.assertEqual(value["status"], "complete")
        self.assertEqual(value["metadata"]["id"], "video-id")
        self.assertEqual(len(value["segments"]), 3)
        self.assertEqual(len(self.downloads), 9)
        self.assertEqual(len(self.agent.run.call_args.kwargs["image_paths"]), 18)
        for segment in value["segments"]:
            self.assertEqual(len(segment["frames"]), 6)
            self.assertIsNotNone(segment["analysis"])
            self.assertTrue((path.parent / segment["clip"]).is_file())
            for f in segment["frames"]:
                self.assertAlmostEqual(f["source_seconds"], segment["start_seconds"] + f["clip_seconds"], places=3)
        collection = read_yaml(write_reference_collection(self.root, [path]))
        self.assertIn("segment-01", collection["consolidated_brief"])
        self.assertTrue(Path(collection["sources"][0]["segments"][0]["clip"]).is_absolute())

    def test_repeated_run_reuses_valid_media_and_analysis(self):
        path = self.extract()
        first = path.read_bytes()
        self.extract()
        self.assertEqual(path.read_bytes(), first)
        self.assertEqual(len(self.downloads), 9)
        self.agent.run.assert_called_once()

    def test_configuration_source_or_transcript_changes_invalidate_cache(self):
        previous = read_json(self.extract())["fingerprint"]
        self.config = replace(self.config, visual_references=replace(self.config.visual_references, frames_per_clip=3))
        second = read_json(self.extract())["fingerprint"]
        self.assertNotEqual(previous, second)
        write_json(self.source / "transcript.json", {"segments": [{"start": 9, "end": 10}]})
        third = read_json(self.extract())["fingerprint"]
        self.assertNotEqual(second, third)
        write_json(self.source / "source.json", {"id": "source-01", "source": "https://example.com/other"})
        self.assertNotEqual(third, read_json(self.extract())["fingerprint"])

    def test_missing_or_corrupted_media_is_regenerated(self):
        path = self.extract()
        clip = path.parent / read_json(path)["segments"][0]["clip"]
        clip.write_bytes(b"corruption")
        self.extract()
        self.assertEqual(clip.read_bytes(), b"clip")
        self.assertEqual(self.agent.run.call_count, 2)

    def test_analysis_failure_keeps_media_and_retries_without_downloads(self):
        self.agent.run.side_effect = AgentError("model cannot inspect images")
        value = read_json(self.extract())
        self.assertEqual(value["status"], "partial")
        self.assertEqual(len(value["segments"]), 3)
        self.assertIn("model cannot", value["errors"][-1]["error"])
        self.agent.run.side_effect = self.analyze
        self.assertEqual(read_json(self.extract())["status"], "complete")
        self.assertEqual(len(self.downloads), 9)

    def test_download_failure_missing_dependency_and_unsupported_sources(self):
        with patch.object(ReferenceExtractor, "run", side_effect=VisualReferenceError("Video unavailable: check URL or cookies")):
            value = read_json(self.extract())
            self.assertEqual(value["status"], "failed")
            self.assertIn("check URL", value["errors"][0]["error"])
        with patch("obscript.visual_references.shutil.which", return_value=None):
            value = read_json(self.extract())
            self.assertIn("Missing dependency", value["errors"][0]["error"])
        write_json(self.source / "source.json", {"id": "source-01", "source": "transcript.txt"})
        self.assertEqual(read_json(self.extract())["status"], "unavailable")
        self.agent.run.assert_not_called()

    def test_disabled_mode_never_downloads_or_invokes_agent(self):
        self.config = replace(self.config, visual_references=VisualReferenceConfig(enabled=False))
        self.assertEqual(read_json(self.extract())["status"], "disabled")
        self.assertFalse(self.downloads)
        self.agent.run.assert_not_called()

    def test_playlist_live_drm_or_missing_duration_do_not_download(self):
        for metadata in [{"_type": "playlist"}, {"is_live": True}, {"has_drm": True}, {"duration": 0}]:
            with self.subTest(metadata=metadata), patch.object(ReferenceExtractor, "run", return_value=
                    subprocess.CompletedProcess([], 0, json.dumps(metadata), "")):
                value = read_json(self.extract())
            self.assertEqual(value["status"], "failed")
            self.assertFalse(value["segments"])
        self.assertFalse(self.downloads)

    def test_analysis_recovery_with_cached_media_needs_no_download_tools(self):
        self.agent.run.side_effect = AgentError("temporary agent failure")
        self.extract()
        self.agent.run.side_effect = self.analyze
        with patch("obscript.visual_references.shutil.which", return_value=None):
            value = read_json(self.extract())
        self.assertEqual(value["status"], "complete")
        self.assertEqual(len(self.downloads), 9)

    def test_partial_download_success_retains_useful_segments(self):
        def download(extractor, url, start, end, destination):
            if destination.name.startswith("segment-02"):
                raise VisualReferenceError("section inaccessible")
            return self.section(extractor, url, start, end, destination)
        self.section_mock.side_effect = download
        value = read_json(self.extract())
        self.assertEqual(value["status"], "partial")
        self.assertEqual(len(value["segments"]), 2)
        self.assertTrue(value["consolidated_brief"])

    def test_invalid_analysis_evidence_and_unknown_only_are_rejected(self):
        value = read_json(self.extract())
        analysis = analysis_fixture(value["segments"])
        schema = read_json(REPO / "schemas/visual-analysis.schema.json")
        analysis["segments"][0]["composition_framing"]["evidence"][0]["source_seconds"] += 5
        with self.assertRaisesRegex(ContractError, "original timestamp"):
            validate_analysis(analysis, value["segments"], schema)
        for s in analysis["segments"]:
            s["composition_framing"] = {"status": "unknown", "description": "Cannot inspect frames", "evidence": []}
        with self.assertRaisesRegex(ContractError, "image-capable"):
            validate_analysis(analysis, value["segments"], schema)

    def test_cited_uncertainty_preserves_useful_analysis_and_cache_reuse(self):
        def analyze(**kwargs):
            analysis, path = self.analyze(**kwargs)
            artifact = read_json(self.source / "visual-references/reference.json")
            frame = artifact["segments"][0]["frames"][0]
            analysis["segments"][0]["camera_motion_graphics"] = {
                "status": "unknown", "description": "This still frame cannot establish camera movement.",
                "evidence": [{"frame_path": frame["path"], "source_seconds": frame["source_seconds"]}],
            }
            return analysis, path
        self.agent.run.side_effect = analyze
        artifact = read_json(self.extract())
        self.assertEqual(artifact["status"], "complete")
        self.assertTrue(artifact["consolidated_brief"])
        field = artifact["segments"][0]["analysis"]["camera_motion_graphics"]
        self.assertEqual(field["status"], "unknown")
        self.assertEqual(len(field["evidence"]), 1)
        downloads = len(self.downloads)
        self.extract()
        self.agent.run.assert_called_once()
        self.assertEqual(len(self.downloads), downloads)

    def test_unknown_citations_still_require_real_frames_and_timestamps(self):
        artifact = read_json(self.extract())
        schema = read_json(REPO / "schemas/visual-analysis.schema.json")
        frame = artifact["segments"][0]["frames"][0]
        for evidence in [
            {"frame_path": "invented.jpg", "source_seconds": frame["source_seconds"]},
            {"frame_path": frame["path"], "source_seconds": frame["source_seconds"] + 5},
        ]:
            with self.subTest(evidence=evidence):
                analysis = analysis_fixture(artifact["segments"])
                analysis["segments"][0]["camera_motion_graphics"]["evidence"] = [evidence]
                with self.assertRaisesRegex(ContractError, "original timestamp"):
                    validate_analysis(analysis, artifact["segments"], schema)
        analysis = analysis_fixture(artifact["segments"])
        analysis["segments"][0]["camera_motion_graphics"] = {
            "status": "observed", "description": "Camera moves.",
            "evidence": [{"frame_path": frame["path"], "source_seconds": frame["source_seconds"]}],
        }
        with self.assertRaisesRegex(ContractError, "two distinct frames"):
            validate_analysis(analysis, artifact["segments"], schema)


class HarnessAndCommandTests(unittest.TestCase):
    def test_codex_and_opencode_receive_image_attachments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = (root / "one.jpg", root / "two.jpg")
            analysis = {"segments": [], "consolidated_brief": "Test"}
            for adapter, module, flag in [(CodexAgent, "codex_agent", "--image"), (OpenCodeAgent, "opencode_agent", "--file")]:
                agent = adapter(executable=Path("agent"), repo_root=REPO, project_root=root,
                                model=None, reasoning_effort="medium", verbose=False)
                def execute(command, **kwargs):
                    if "--output-last-message" in command:
                        Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps(analysis))
                        stdout = ""
                    else:
                        stdout = json.dumps({"type": "text", "part": {"text": json.dumps(analysis)}})
                    return subprocess.CompletedProcess(command, 0, stdout, "")
                # Use a regular schema fixture for adapter validation; analysis validation is tested separately.
                from test_visual_production import script_fixture
                analysis = script_fixture()
                with patch(f"obscript.{module}.subprocess.run", side_effect=execute) as run:
                    agent.run(stage="visual", skill="analyze-visual-reference", schema="script", prompt="Inspect", image_paths=images)
                command = run.call_args.args[0]
                self.assertEqual(command.count(flag), 2)
                self.assertIn(str(images[0]), command)
                self.assertIn(str(images[1]), command)

    def test_section_commands_enforce_ranges_auth_low_resolution_and_no_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = replace(config_fixture(root), cookies=Path("cookies.txt"), cookies_from_browser=None)
            extractor = ReferenceExtractor(runtime, root)
            commands = []
            destination = extractor.root / "segment.mp4"
            def run(command, **kwargs):
                commands.append(command)
                if "--download-sections" in command:
                    Path(command[command.index("--output") + 1].replace("%(ext)s", "mp4")).write_bytes(b"download")
                elif "-show_entries" in command:
                    return subprocess.CompletedProcess(command, 0, json.dumps({"format": {"duration": "15"}, "streams": [{"codec_type": "video"}]}), "")
                else:
                    Path(command[-1]).write_bytes(b"clip")
                return subprocess.CompletedProcess(command, 0, "", "")
            with patch.object(extractor, "run", side_effect=run):
                extractor.section("https://example.com/video", 20., 35., destination)
                extractor.section("https://example.com/video", 20., 35., destination)
            self.assertEqual(len(commands), 3)
            self.assertIn("*20.000-35.000", commands[0])
            self.assertIn("--force-keyframes-at-cuts", commands[0])
            self.assertIn("bv[height<=480]/b[height<=480]", commands[0])
            self.assertIn("--cookies", commands[0])
            self.assertIn("-an", commands[1])

    def test_tool_failure_and_timeout_are_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            extractor = ReferenceExtractor(config_fixture(Path(directory)), Path(directory))
            with patch("obscript.visual_references.subprocess.Popen", side_effect=FileNotFoundError()):
                with self.assertRaisesRegex(VisualReferenceError, "Missing dependency"):
                    extractor.run(["yt-dlp"])
            with patch("obscript.visual_references.subprocess.Popen") as popen, patch("obscript.visual_references.os.killpg") as kill:
                process = popen.return_value.__enter__.return_value
                process.communicate.side_effect = [subprocess.TimeoutExpired("ffmpeg", 180), ("", "")]
                with self.assertRaisesRegex(VisualReferenceError, "increase --visual-reference-timeout"):
                    extractor.run(["ffmpeg"])
                kill.assert_called_once()

    def test_cli_validation_and_dry_run_integration(self):
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(main(["https://example.com/video", "--render", "--dry-run"]), 0)
        self.assertIn("visual-references", stdout.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(main(["source", "--dry-run", "--visual-reference-clips", "0"]), 1)
        self.assertIn("clip_count", stderr.getvalue())


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools unavailable")
class RealMediaTests(unittest.TestCase):
    def test_section_normalization_and_probe_are_real_ffmpeg_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = replace(config_fixture(root), cookies_from_browser=None)
            extractor = ReferenceExtractor(runtime, root)
            original = root / "original.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "testsrc2=size=160x90:rate=10", "-t", "3", "-an", "-c:v", "libx264", str(original)], check=True)
            run_media = extractor.run
            def run(command, **kwargs):
                if "--download-sections" in command:
                    output = command[command.index("--output") + 1].replace("%(ext)s", "mp4")
                    shutil.copy2(original, output)
                    return subprocess.CompletedProcess(command, 0, "", "")
                return run_media(command, **kwargs)
            destination = extractor.root / "segment.mp4"
            with patch.object(extractor, "run", side_effect=run) as commands:
                extractor.section("https://example.com/video", 22., 25., destination)
                self.assertEqual(commands.call_count, 3)
                extractor.section("https://example.com/video", 22., 25., destination)
                self.assertEqual(commands.call_count, 3)
            self.assertGreater(destination.stat().st_size, 1000)
            self.assertTrue(destination.with_suffix(".receipt.json").is_file())
            self.assertFalse(list(destination.parent.glob("*.download.*")))

    def test_real_decoding_frame_extraction_and_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extractor = ReferenceExtractor(config_fixture(root), root)
            clip = extractor.root / "segment.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "testsrc2=size=160x90:rate=10", "-t", "3", "-an", "-c:v", "libx264", str(clip)], check=True)
            features, changes = extractor.features(clip)
            self.assertEqual(len(features), 61)
            self.assertEqual(len(changes), 5)
            frames = extractor.frames(clip, 22., 3., changes)
            self.assertEqual(len(frames), 6)
            for frame in frames:
                path = extractor.root / frame["path"]
                self.assertGreater(path.stat().st_size, 100)
                self.assertTrue(22 <= frame["source_seconds"] < 25)


if __name__ == "__main__":
    unittest.main()
