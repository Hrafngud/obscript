from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from obscript.cli import main
from obscript.contracts import ContractError, parse_command_tokens
from obscript.models import RuntimeConfig, SourceAsset
from obscript.pipeline import Pipeline
from obscript.production import ProductionAgent, ProductionError, invalidate_downstream, probe_media, validate_storybook
from obscript.storage import format_timestamp, read_json, render_script, render_storybook, write_json, write_yaml

REPO = Path(__file__).resolve().parents[1]


def script_fixture() -> dict:
    return {
        "schema_version": "1", "language": "pt-BR", "title": "Padrões", "thesis": "Veja a causa.",
        "metadata": {"format": "source", "pipeline": "single", "time_controller": "normal", "target_duration_seconds": 12},
        "sections": [
            {"id": section_id, "title": section_id, "type": kind, "purpose": "Explicar", "topic_refs": [],
             "estimated_seconds": seconds, "narration": narration}
            for section_id, kind, seconds, narration in [
                ("hook", "hook", 6, "Você observa o padrão. Agora veja a causa."),
                ("body", "body", 3, "A causa explica o padrão."),
                ("end", "conclusion", 3, "Observe a relação com cuidado."),
            ]
        ],
    }


def scene_fixture(order: int, section_id: str, text: str) -> dict:
    return {
        "id": f"scene-{order:03d}", "order": order, "script_section_id": section_id,
        "voiceover": {"text": text, "estimated_seconds": 3},
        "timing": {"estimated_start_seconds": (order - 1) * 3, "estimated_end_seconds": order * 3},
        "narrative_beat": "Explicar a relação", "visual_goal": "Entender o padrão",
        "composition": {"layout": "Centro", "focal_element": "Nó", "supporting_elements": []},
        "visual_elements": [{"type": "diagrama", "content": "Nó conectado", "role": "Relação"}],
        "onscreen_text": [{"text": "Observe a causa", "purpose": "Ênfase"}],
        "animation": {key: "Nenhuma" for key in ["entrance", "continuous", "emphasis", "exit", "camera"]},
        "transition_out": "Corte direto" if order < 4 else "Nenhuma", "asset_requirements": [],
        "render_brief": "Mostre o nó no centro.",
    }


def story_fixture() -> dict:
    return {"schema_version": "2", "target_duration_seconds": 12, "scenes": [
        scene_fixture(1, "hook", "Você observa o padrão."),
        scene_fixture(2, "hook", "Agora veja a causa."),
        scene_fixture(3, "body", "A causa explica o padrão."),
        scene_fixture(4, "end", "Observe a relação com cuidado."),
    ]}


def direction_fixture() -> dict:
    def fill(schema: dict):
        if "const" in schema:
            return schema["const"]
        if schema["type"] == "object":
            return {name: fill(child) for name, child in schema["properties"].items()}
        if schema["type"] == "array":
            return []
        if schema["type"] == "integer":
            return 8
        return "Identidade definida"
    return fill(read_json(REPO / "schemas/creative-direction.schema.json"))


def config_fixture(root: Path, review_passes: int = 2) -> RuntimeConfig:
    return RuntimeConfig(REPO, root / "outputs", root / "transcripts", Path("ytstt"), Path("codex"),
                         None, "medium", review_passes, "teste", False)


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        return read_json(path)
    return yaml.safe_load(path.read_text())


class StorybookValidationTests(unittest.TestCase):
    def test_exact_coverage_with_whitespace_normalization(self):
        story = story_fixture()
        story["scenes"][0]["voiceover"]["text"] = "Você  observa\no padrão."
        validate_storybook(script_fixture(), story, 12)

    def test_on_screen_text_has_no_fixed_word_limit(self):
        for text in ["−70 · −50 · −10 · +5 mV", "um dois três quatro cinco seis sete oito nove",
                     "Uma explicação com contexto suficiente para ler sem um limite arbitrário de palavras."]:
            with self.subTest(text=text):
                story = story_fixture()
                story["scenes"][0]["onscreen_text"][0]["text"] = text
                validate_storybook(script_fixture(), story, 12)

    def test_rejects_narration_defects(self):
        changes = {
            "invented": "Você observa outro padrão.",
            "omitted": "Você observa.",
            "duplicated": "Você observa o padrão. Você observa o padrão.",
            "reordered": "o padrão. Você observa",
            "spans_sections": "Você observa o padrão. A causa explica o padrão.",
            "empty": " ",
        }
        for defect, text in changes.items():
            with self.subTest(defect=defect):
                story = story_fixture()
                story["scenes"][0]["voiceover"]["text"] = text
                with self.assertRaises(ContractError):
                    validate_storybook(script_fixture(), story, 12)

    def test_rejects_sequence_and_timing_defects(self):
        changes = [
            (0, "id", "scene-002"), (1, "order", 3),
            (1, "script_section_id", "unknown"), (1, "script_section_id", "end"),
            (0, "timing.estimated_start_seconds", 1),
            (1, "timing.estimated_start_seconds", 2),
            (1, "timing.estimated_start_seconds", 4),
            (1, "timing.estimated_start_seconds", 3.00000001),
            (3, "timing.estimated_end_seconds", 11),
            (0, "timing.estimated_end_seconds", float("nan")),
            (0, "voiceover.estimated_seconds", 0),
            (0, "script_section_id", ["hook", "body"]),
        ]
        for index, field, value in changes:
            with self.subTest(field=field, value=value):
                story = story_fixture()
                obj = story["scenes"][index]
                parts = field.split(".")
                for part in parts[:-1]:
                    obj = obj[part]
                obj[parts[-1]] = value
                with self.assertRaises(ContractError):
                    validate_storybook(script_fixture(), story, 12)

    def test_missing_section_and_reordered_excerpts(self):
        for defect in ["missing", "reordered"]:
            story = story_fixture()
            if defect == "missing":
                story["scenes"][2]["script_section_id"] = "hook"
            else:
                a, b = story["scenes"][:2]
                a["voiceover"]["text"], b["voiceover"]["text"] = b["voiceover"]["text"], a["voiceover"]["text"]
            with self.subTest(defect=defect), self.assertRaises(ContractError):
                validate_storybook(script_fixture(), story, 12)

    def test_audio_assets_rejected_before_rendering(self):
        for kind in ["audio", "voiceover", "tts", "bgm", "sfx", "música"]:
            with self.subTest(kind=kind):
                story = story_fixture()
                story["scenes"][0]["asset_requirements"] = [{"type": kind, "description": "Recurso"}]
                with self.assertRaisesRegex(ContractError, "audio assets"):
                    validate_storybook(script_fixture(), story, 12)

    def test_duration_mismatch_and_duplicate_script_ids(self):
        with self.assertRaises(ContractError):
            validate_storybook(script_fixture(), story_fixture(), 13)
        script = script_fixture()
        script["sections"][1]["id"] = "hook"
        with self.assertRaises(ContractError):
            validate_storybook(script, story_fixture(), 12)


class FakePlanningAgent:
    calls: list[tuple[str, Path]] = []
    verdicts: list[str] = []
    invalid_storybooks = 0
    split_parts = 2

    def __init__(self, **kwargs):
        self.root = kwargs["project_root"]
        self.state = self.root / ".obscript"
        self.state.mkdir(parents=True, exist_ok=True)
        self.counter = 0

    def run(self, *, stage, skill, prompt, schema):
        self.counter += 1
        self.calls.append((stage, self.root))
        if skill == "analyze-source" or skill == "remix":
            value = {"recommended_duration_seconds": 12, "sources": [{"title": "Fonte"}], "summary": {"thesis": "Tese"}}
        elif skill == "split":
            value = {"rationale": "Conceitos independentes", "parts": [
                {"recommended_duration_seconds": 12, "summary": {"thesis": "Tese"}} for _ in range(self.split_parts)]}
        elif skill == "plan-script":
            value = {"title": "Plano", "thesis": "Tese", "format": "source", "target_duration_seconds": 12,
                     "hook": {"idea": "Gancho"}, "sections": [
                         {"title": "Corpo", "type": "body", "purpose": "Explicar", "estimated_seconds": 12,
                          "topic_refs": [], "transition": "Conclusão"}]}
        elif skill == "write-script":
            value = script_fixture()
        elif skill == "review-script":
            value = {"verdict": self.verdicts.pop(0) if self.verdicts else "pass", "recommendation": {"rerun": []}}
        elif skill == "creative-direction":
            value = direction_fixture()
            assert "approved-script.json" in prompt
        elif skill == "storybook":
            value = story_fixture()
            if self.invalid_storybooks:
                type(self).invalid_storybooks -= 1
                value["scenes"][0]["voiceover"]["text"] = "Texto inventado."
        else:
            raise AssertionError(skill)
        path = self.state / f"{self.counter:02d}-{stage}.json"
        write_json(path, value)
        return value, path


class PipelineVisualTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.transcript = self.root / "transcript.txt"
        self.transcript.write_text("Fonte")
        self.asset = SourceAsset("source", "Fonte", self.transcript, None, None, "pt-BR", 12)
        FakePlanningAgent.calls = []
        FakePlanningAgent.verdicts = []
        FakePlanningAgent.invalid_storybooks = 0
        self.addCleanup(patch.stopall)
        patch("obscript.pipeline.CodexAgent", FakePlanningAgent).start()
        patch("obscript.pipeline.ingest_source", return_value=[self.asset]).start()
        self.producer = patch("obscript.pipeline.ProductionAgent").start()
        patch("sys.stdout", new=io.StringIO()).start()

    def run_pipeline(self, tokens=None, render=False):
        return Pipeline(config_fixture(self.root)).run(parse_command_tokens(tokens or ["source"], render=render))

    def test_long_on_screen_text_does_not_trigger_retries(self):
        original_run = FakePlanningAgent.run
        label = "−70 · −50 · −10 · +5 mV · Potenciais testados"
        def with_long_label(agent, **kwargs):
            value, path = original_run(agent, **kwargs)
            if kwargs["skill"] == "storybook":
                value["scenes"][0]["onscreen_text"][0]["text"] = label
                write_json(path, value)
            return value, path
        with patch.object(FakePlanningAgent, "run", with_long_label):
            result = self.run_pipeline()
        stages = [stage for stage, _ in FakePlanningAgent.calls]
        self.assertIn("storybook-01", stages)
        self.assertNotIn("storybook-02", stages)
        self.assertIn(label, (result.project_root / "storybook.md").read_text())
        self.assertTrue((result.project_root / "storybook.yaml").exists())

    def test_default_preproduction_without_media_calls(self):
        result = self.run_pipeline()
        self.assertTrue(result.passed_review)
        self.assertEqual([path.name for path in result.outputs], ["script.md", "creative-direction.md", "storybook.md", "storybook.yaml"])
        validate_storybook(read_json(result.project_root / ".obscript/approved-script.json"),
                          read_json(result.project_root / ".obscript/storybook.json"), 12)
        self.producer.assert_not_called()
        self.assertFalse((result.project_root / "production.yaml").exists())
        script_text = (result.project_root / "script.md").read_text()
        self.assertIn("hook · 00:00:00.000 → 00:00:06.000", script_text)
        self.assertIn("scene-004 · 00:00:09.000 → 00:00:12.000", script_text)

    def test_unresolved_review_gates_all_visual_stages(self):
        FakePlanningAgent.verdicts = ["revise", "revise"]
        result = self.run_pipeline(render=True)
        self.assertFalse(result.passed_review)
        stages = [stage for stage, _ in FakePlanningAgent.calls]
        self.assertNotIn("creative-direction", stages)
        self.producer.assert_not_called()
        self.assertTrue((result.project_root / "script.md").exists())
        self.assertTrue((result.project_root / "review.yaml").exists())
        for name in ["creative-direction.md", "storybook.md", "storybook.yaml", "production.yaml", "video.mp4"]:
            self.assertFalse((result.project_root / name).exists())

    def test_review_revision_passes_before_visuals(self):
        FakePlanningAgent.verdicts = ["revise", "pass"]
        self.run_pipeline(render=True)
        stages = [stage for stage, _ in FakePlanningAgent.calls]
        self.assertEqual(stages.count("write-script"), 2)
        self.assertGreater(stages.index("creative-direction"), max(i for i, stage in enumerate(stages) if stage == "review-script"))
        self.producer.return_value.produce.assert_called_once()

    def test_invalid_storybook_regenerated_and_never_rendered(self):
        FakePlanningAgent.invalid_storybooks = 1
        result = self.run_pipeline()
        self.assertTrue((result.project_root / ".obscript/storybook-01.validation.json").exists())
        self.assertIn("storybook-02", [stage for stage, _ in FakePlanningAgent.calls])
        self.assertIn("status: validated", (result.project_root / "storybook.md").read_text())
        self.producer.assert_not_called()

    def test_retry_limit_stops_render(self):
        FakePlanningAgent.invalid_storybooks = 3
        with self.assertRaisesRegex(ContractError, "after 3 attempts"):
            self.run_pipeline(render=True)
        self.producer.assert_not_called()
        self.assertFalse((self.root / "outputs/teste/storybook.yaml").exists())
        draft_path = self.root / "outputs/teste/storybook.md"
        self.assertTrue(draft_path.exists())
        draft = draft_path.read_text()
        self.assertIn("status: invalid", draft)
        self.assertIn("voiceover differs from approved narration", draft)
        self.assertIn("produção bloqueada", draft)

    def test_split_and_playlist_units_own_all_visual_state(self):
        for tokens, playlist in [(["split", "source"], False), (["source"], True)]:
            with self.subTest(tokens=tokens):
                if playlist:
                    patch("obscript.pipeline.ingest_source", return_value=[self.asset, self.asset]).start()
                result = self.run_pipeline(tokens)
                for number in [1, 2]:
                    unit = result.project_root / f"video-{number:02d}"
                    for name in ["knowledge.yaml", "plan.md", "script.md", "review.yaml", "creative-direction.md", "storybook.md", "storybook.yaml",
                                 ".obscript/approved-script.json", ".obscript/creative-direction.json", ".obscript/storybook.json"]:
                        self.assertTrue((unit / name).exists(), name)

    def test_script_revision_archives_stale_visuals(self):
        result = self.run_pipeline()
        unit = result.project_root
        (unit / "video.mp4").write_bytes(b"stale video")
        write_json(unit / "production.yaml", {"status": "complete"})
        FakePlanningAgent.verdicts = ["revise", "revise"]
        agent = FakePlanningAgent(project_root=unit)
        approved = Pipeline(config_fixture(self.root))._produce_script(agent, parse_command_tokens(["source"]), unit,
                                                                      {"recommended_duration_seconds": 12})
        self.assertIsNone(approved)
        for name in ["creative-direction.md", "storybook.md", "storybook.yaml", "production.yaml", "video.mp4", ".obscript/approved-script.json"]:
            self.assertFalse((unit / name).exists())
        self.assertTrue(list((unit / ".obscript/invalidated").rglob("video.mp4")))


class ProductionExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = {name: self.root / ".obscript" / f"{name}.json" for name in ["script", "direction", "storybook", "review"]}
        for name, value in [("script", script_fixture()), ("direction", direction_fixture()), ("storybook", story_fixture()), ("review", {"verdict": "pass"})]:
            write_json(self.paths[name], value)
        self.agent = ProductionAgent(config_fixture(self.root), self.root)
        self.calls = []
        self.failure = None
        self.mutate = False
        self.duration = 12.0
        self.scene_duration = 3.0
        self.escape_output = False
        self.missing_scene = None

    def produce(self):
        return self.agent.produce(script_path=self.paths["script"], direction_path=self.paths["direction"],
                                  storybook_path=self.paths["storybook"], review_path=self.paths["review"])

    def execute_fixture(self, stage, request_path, output_dir):
        self.calls.append(stage)
        request = read_json(request_path)
        if self.mutate:
            self.paths["script"].write_text("changed upstream")
        self.assertEqual(request["operation"], "video")
        self.assertEqual(request["storybook"], story_fixture())
        self.assertEqual(request["audio_policy"], "none")
        self.assertFalse(request["hyperframes"]["render"]["audio"])
        self.assertEqual(request["hyperframes"]["brief"]["narration"], "no")
        self.assertTrue(request["hyperframes"]["render_authorized"])
        self.assertEqual(request["creative_direction"], direction_fixture())
        self.assertEqual(request["target_duration_seconds"], 12)
        self.assertEqual(request["hyperframes"]["project_directory"], str(output_dir / "hyperframes"))
        for scene, output in zip(request["storybook"]["scenes"], request["scene_outputs"]):
            self.assertEqual(output["scene_id"], scene["id"])
            if scene["id"] == self.failure:
                raise ProductionError("Synthetic backend failure")
            if scene["id"] == self.missing_scene:
                continue
            scene_dir = Path(output["output_directory"])
            (scene_dir / "scene.mp4").write_bytes(b"scene fixture")
            write_json(Path(output["manifest"]), {
                "scene_id": scene["id"], "script_section_id": scene["script_section_id"], "generator": "hyperframes",
                "status": "complete", "estimated_duration_seconds": 3, "actual_duration_seconds": 3,
                "output_files": ["../escape.mp4"] if self.escape_output else ["scene.mp4"],
            })
        if self.failure == "assembly":
            raise ProductionError("Synthetic backend failure")
        Path(request["output_video"]).write_bytes(b"assembled fixture")

    def probe_fixture(self, path):
        return self.duration if path.name == "assembled.mp4" else self.scene_duration

    def patched_produce(self):
        with patch.object(self.agent, "_execute", side_effect=self.execute_fixture), patch("obscript.production.probe_media", side_effect=self.probe_fixture), patch("obscript.production.shutil.which", return_value="ffprobe"):
            return self.produce()

    def test_single_run_produces_complete_storybook_and_actual_duration(self):
        output = self.patched_produce()
        self.assertEqual(output, self.root / "video.mp4")
        self.assertEqual(self.calls, ["produce-video"])
        self.assertEqual(len(list((self.root / ".obscript").glob("*.request.json"))), 1)
        manifest = load_yaml(self.root / "production.yaml")
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["backend"], "hyperframes")
        self.assertFalse(manifest["audio"])
        self.assertEqual(manifest["actual_duration_seconds"], 12)
        self.assertEqual(manifest["target_duration_seconds"], 12)
        self.assertEqual(manifest["final_video"], "video.mp4")

    def test_scene_failure_keeps_prior_scene_and_blocks_assembly(self):
        self.failure = "scene-002"
        with self.assertRaises(ProductionError):
            self.patched_produce()
        manifest = load_yaml(self.root / "production.yaml")
        self.assertEqual([item["status"] for item in manifest["scenes"]], ["complete", "failed", "pending", "pending"])
        self.assertEqual(read_json(self.root / "production/scenes/scene-002/manifest.json")["status"], "failed")
        self.assertIsNone(manifest["final_video"])
        self.assertFalse((self.root / "video.mp4").exists())
        self.assertEqual(self.calls, ["produce-video"])

    def test_assembly_failure_never_publishes_final_video(self):
        self.failure = "assembly"
        with self.assertRaises(ProductionError):
            self.patched_produce()
        manifest = load_yaml(self.root / "production.yaml")
        self.assertEqual(manifest["status"], "failed")
        self.assertTrue(all(item["status"] == "complete" for item in manifest["scenes"]))
        self.assertIsNone(manifest["final_video"])
        self.assertFalse((self.root / "video.mp4").exists())

    def test_duration_mismatch_blocks_publication(self):
        self.duration = 16
        with self.assertRaisesRegex(ProductionError, "duration differs"):
            self.patched_produce()
        self.assertFalse((self.root / "video.mp4").exists())

    def test_executor_failure_blocks_publication_even_with_all_outputs(self):
        def fail_after_render(stage, request_path, output_dir):
            self.execute_fixture(stage, request_path, output_dir)
            raise ProductionError("Executor failed after rendering")
        with patch.object(self.agent, "_execute", side_effect=fail_after_render), patch("obscript.production.probe_media", side_effect=self.probe_fixture), patch("obscript.production.shutil.which", return_value="ffprobe"):
            with self.assertRaisesRegex(ProductionError, "Executor failed after rendering"):
                self.produce()
        manifest = load_yaml(self.root / "production.yaml")
        self.assertTrue(all(item["status"] == "complete" for item in manifest["scenes"]))
        self.assertEqual(manifest["status"], "failed")
        self.assertIsNone(manifest["final_video"])
        self.assertTrue((self.root / "production/assembled.mp4").exists())
        self.assertFalse((self.root / "video.mp4").exists())

    def test_scene_duration_drift_blocks_publication(self):
        self.scene_duration = 4
        with self.assertRaisesRegex(ProductionError, "scene-001: animation duration differs"):
            self.patched_produce()
        self.assertEqual(self.calls, ["produce-video"])
        self.assertFalse((self.root / "video.mp4").exists())
        self.assertEqual(load_yaml(self.root / "production.yaml")["scenes"][0]["status"], "failed")

    def test_mutating_upstream_restores_input_and_fails(self):
        original = self.paths["script"].read_bytes()
        self.mutate = True
        with self.assertRaisesRegex(ProductionError, "immutable upstream"):
            self.patched_produce()
        self.assertEqual(self.paths["script"].read_bytes(), original)
        self.assertEqual(load_yaml(self.root / "production.yaml")["status"], "failed")

    def test_unsafe_scene_output_rejected(self):
        self.escape_output = True
        with self.assertRaisesRegex(ProductionError, "invalid scene output"):
            self.patched_produce()

    def test_review_gate_prevents_executor(self):
        write_json(self.paths["review"], {"verdict": "revise"})
        with patch.object(self.agent, "_execute") as execute, self.assertRaisesRegex(ProductionError, "approved script"):
            self.produce()
        execute.assert_not_called()
        self.assertFalse((self.root / "production").exists())

    def test_missing_probe_fails_before_media_calls(self):
        with patch("obscript.production.shutil.which", return_value=None), patch.object(self.agent, "_execute") as execute:
            with self.assertRaisesRegex(ProductionError, "ffprobe is required"):
                self.produce()
        execute.assert_not_called()
        self.assertEqual(load_yaml(self.root / "production.yaml")["status"], "failed")

    def test_canonical_yaml_plan_is_read_and_revalidated(self):
        story = story_fixture()
        story["scenes"][0]["voiceover"]["text"] = "Uma alteração não aprovada."
        yaml_path = self.root / "storybook.yaml"
        write_yaml(yaml_path, story)
        with patch.object(self.agent, "_execute") as execute, self.assertRaisesRegex(ContractError, "voiceover differs"):
            self.agent.produce(script_path=self.paths["script"], direction_path=self.paths["direction"],
                               storybook_path=yaml_path, review_path=self.paths["review"])
        execute.assert_not_called()

    def test_missing_scene_blocks_publication_even_when_assembly_exists(self):
        self.missing_scene = "scene-002"
        with self.assertRaisesRegex(ProductionError, "Invalid scene manifest"):
            self.patched_produce()
        self.assertTrue((self.root / "production/assembled.mp4").exists())
        self.assertFalse((self.root / "video.mp4").exists())
        self.assertEqual(load_yaml(self.root / "production.yaml")["status"], "failed")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools unavailable")
    def test_local_media_assembly_publishes_verified_mp4(self):
        fixture = self.root / "fixture.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=32x32:r=24",
                        "-t", "3", "-c:v", "mpeg4", "-an", str(fixture)], check=True, capture_output=True)
        def local_executor(stage, request_path, output_dir):
            request = read_json(request_path)
            self.execute_fixture(stage, request_path, output_dir)
            paths = [Path(item["output_directory"]) / "scene.mp4" for item in request["scene_outputs"]]
            for path in paths:
                shutil.copy2(fixture, path)
            command = ["ffmpeg", "-v", "error"]
            for path in paths:
                command.extend(["-i", str(path)])
            command.extend(["-filter_complex", "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v]",
                            "-map", "[v]", "-c:v", "mpeg4", "-an", "-y", request["output_video"]])
            subprocess.run(command, check=True, capture_output=True)
        with patch.object(self.agent, "_execute", side_effect=local_executor):
            video = self.produce()
        self.assertAlmostEqual(probe_media(video), 12, delta=0.04)
        self.assertEqual(load_yaml(self.root / "production.yaml")["status"], "complete")

    def test_production_executor_has_write_boundary_without_schema(self):
        output = self.root / "production"
        output.mkdir(parents=True)
        request = self.root / ".obscript/request.json"
        write_json(request, {})
        with patch("obscript.production.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "done", "")) as run:
            self.agent._execute("produce-video", request, output)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(command[command.index("-C") + 1], str(output))
        self.assertNotIn("--output-schema", command)
        self.assertIn("$hyperframes", run.call_args.kwargs["input"])
        self.assertIn("Do not launch nested Codex runs", run.call_args.kwargs["input"])
        self.assertTrue((output / "executor.log").exists())


class InvalidationAndDryRunTests(unittest.TestCase):
    def test_readable_storybook_includes_the_complete_scene_plan(self):
        script, story = script_fixture(), story_fixture()
        story["scenes"][0]["animation"]["camera"] = "Avance lentamente até o nó central."
        story["scenes"][0]["asset_requirements"] = [{"type": "image", "description": "Ilustração do nó"}]
        text = render_storybook(story, script)
        self.assertIn("status: validated", text)
        self.assertIn("[Roteiro com tempos](script.md)", text)
        self.assertIn("## Linha do tempo", text)
        self.assertIn("Avance lentamente até o nó central.", text)
        self.assertIn("Ilustração do nó", text)
        for scene in story["scenes"]:
            self.assertIn(f"## {scene['id']} ·", text)
            self.assertIn(scene["voiceover"]["text"], text)
            self.assertIn(scene["render_brief"], text)
        self.assertIn("00:00:09.000 → 00:00:12.000", text)

    def test_invalid_structure_still_has_an_inspectable_markdown_draft(self):
        story = story_fixture()
        scene = story["scenes"][0]
        scene["script_section_id"] = ["hook", "body"]
        scene["timing"]["estimated_start_seconds"] = float("nan")
        scene["composition"] = None
        scene["asset_requirements"] = None
        text = render_storybook(story, script_fixture(), validation_error="Invalid scene structure")
        self.assertIn("status: invalid", text)
        self.assertIn("Invalid scene structure", text)
        self.assertIn("Tempo inválido", text)
        self.assertIn("scene-004", text)

    def test_human_reading_cues_preserve_all_approved_narration(self):
        script, story = script_fixture(), story_fixture()
        text = render_script(script, story)
        for scene in story["scenes"]:
            start = format_timestamp(scene["timing"]["estimated_start_seconds"])
            end = format_timestamp(scene["timing"]["estimated_end_seconds"])
            self.assertIn(f"### {scene['id']} · {start} → {end}\n\n{scene['voiceover']['text']}", text)
            self.assertEqual(text.count(scene["voiceover"]["text"]), 1)
        validate_storybook(script, story, 12)
        self.assertEqual(format_timestamp(3661.125), "01:01:01.125")

    def test_animation_probe_rejects_an_audio_track(self):
        result = subprocess.CompletedProcess([], 0,
            '{"format":{"duration":"3"},"streams":[{"codec_type":"video"},{"codec_type":"audio"}]}', "")
        with patch("obscript.production.subprocess.run", return_value=result):
            with self.assertRaisesRegex(ProductionError, "must not contain an audio track"):
                probe_media(Path("unexpected-audio.mp4"))

    def test_dependency_invalidation_preserves_upstream(self):
        for changed, removed in [
            ("storybook", ["production.yaml", "video.mp4"]),
            ("creative-direction", ["production.yaml", "video.mp4", "storybook.yaml"]),
            ("script", ["production.yaml", "video.mp4", "storybook.yaml", "creative-direction.md"]),
        ]:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for name in ["script.md", "creative-direction.md", "storybook.md", "storybook.yaml", "production.yaml", "video.mp4"]:
                    (root / name).write_text("old artifact")
                invalidate_downstream(root, changed)
                self.assertTrue((root / "script.md").exists())
                for name in removed:
                    self.assertFalse((root / name).exists())
                self.assertTrue(list((root / ".obscript/invalidated").rglob("video.mp4")))

    def test_dry_run_render_validates_without_any_execution(self):
        with patch("obscript.cli.Pipeline") as pipeline, patch("obscript.cli._resolve_codex") as codex, contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(main(["extend", "essay", "VIDEO", "--render", "--dry-run"]), 0)
        pipeline.assert_not_called()
        codex.assert_not_called()
        self.assertIn("validate-storybook → produce-video → package-production", stdout.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["essay", "compress", "VIDEO", "--render", "--dry-run"]), 1)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools unavailable")
    def test_real_media_probe_verifies_silent_video_and_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "fixture.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=32x32:r=24",
                            "-t", "0.5", "-c:v", "mpeg4", "-an", str(video)], check=True, capture_output=True)
            self.assertAlmostEqual(probe_media(video), 0.5, delta=0.05)
            invalid = root / "invalid.mp4"
            invalid.write_text("not video")
            with self.assertRaises(ProductionError):
                probe_media(invalid)


if __name__ == "__main__":
    unittest.main()
