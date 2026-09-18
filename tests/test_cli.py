from __future__ import annotations

import unittest
import contextlib
import io
import tempfile
from unittest.mock import patch
from pathlib import Path
from uuid import UUID

from obscript.cli import build_parser, main
from obscript.contracts import parse_command_tokens
from obscript.projects import create_project
from obscript.models import RuntimeConfig
from obscript.storage import read_json, read_yaml


class NewProjectTests(unittest.TestCase):
    def test_new_creates_manual_project_without_external_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            transcripts = Path(directory) / "transcripts"
            with patch("obscript.cli.Pipeline") as pipeline, patch("obscript.cli._resolve_codex") as codex:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(["new", "A Ilusão da Programação", "--output-dir", str(vault),
                                           "--transcripts-dir", str(transcripts), "--target-duration", "8m",
                                           "--format", "essay"]), 0)
                pipeline.assert_not_called()
                codex.assert_not_called()
            root = vault / "a-ilusao-da-programacao"
            self.assertEqual({path.name for path in root.iterdir()}, {"project.json", "script.md", "run.yaml"})
            metadata = read_json(root / "project.json")
            UUID(metadata["id"])
            self.assertIn(metadata["id"], output.getvalue())
            self.assertEqual((metadata["origin"], metadata["status"], metadata["phase"]),
                             ("original", "draft", "created"))
            self.assertEqual(metadata["command"]["sources"], [])
            self.assertEqual(metadata["command"]["target_duration_seconds"], 480)
            self.assertEqual(metadata["creative_direction"], str(vault / "Globals/creative-direction.md"))
            run = read_yaml(root / "run.yaml")
            self.assertEqual(run["project_id"], metadata["id"])
            self.assertEqual(run["sources"], [])
            self.assertIsNone(run["agent"])
            text = (root / "script.md").read_text()
            self.assertTrue(text.startswith("---\n"))
            for expected in ["language: pt-BR", "format: essay", "target_duration_seconds: 480",
                             "# A Ilusão da Programação", "## Gancho", "## Desenvolvimento", "## Conclusão"]:
                self.assertIn(expected, text)
            self.assertFalse(transcripts.exists())

    def test_bare_new_and_collisions_preserve_existing_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["new", "--vault", directory]), 0)
            first = Path(directory) / "novo-roteiro"
            (first / "script.md").write_text("My own draft")
            self.assertEqual(main(["new", "--vault", directory]), 0)
            self.assertEqual((first / "script.md").read_text(), "My own draft")
            second = Path(directory) / "novo-roteiro-2"
            self.assertTrue((second / "script.md").exists())
            self.assertNotEqual(read_json(first / "project.json")["id"], read_json(second / "project.json")["id"])
            self.assertEqual(read_json(second / "project.json")["command"]["target_duration_seconds"], 600)

    def test_project_name_and_creative_direction_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            direction = Path(directory) / "shared.md"
            self.assertEqual(main(["new", "Título original", "--project", "Pasta personalizada",
                                   "--creative-direction", str(direction), "--vault", directory]), 0)
            root = Path(directory) / "pasta-personalizada"
            self.assertIn("# Título original", (root / "script.md").read_text())
            self.assertEqual(read_json(root / "project.json")["creative_direction"], str(direction))
            self.assertFalse(direction.exists())

    def test_dry_run_and_invalid_options_do_not_create_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["new", "--vault", str(vault), "--dry-run"]), 0)
            self.assertIn("script-template", output.getvalue())
            self.assertFalse(vault.exists())
            for flags in [["--target-duration", "0"], ["--render"], ["--storybook"], ["--into", "2"]]:
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["new", "--vault", str(vault), *flags]), 1)
                self.assertFalse(vault.exists())

    def test_original_project_resume_reports_manual_draft_without_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["new", "--vault", directory]), 0)
            root = Path(directory) / "novo-roteiro"
            project_id = read_json(root / "project.json")["id"]
            with patch("obscript.cli.Pipeline") as pipeline, contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(main([project_id, "--storybook", "--vault", directory]), 1)
                pipeline.assert_not_called()
            self.assertIn("manual drafts", error.getvalue())
            self.assertIn(str(root / "script.md"), error.getvalue())
            self.assertEqual(read_json(root / "project.json")["status"], "draft")


class CliDefaultsTests(unittest.TestCase):
    def test_post_production_requires_project_and_is_exclusive(self) -> None:
        self.assertTrue(build_parser().parse_args(["PROJECT_ID", "--post-production"]).post_production)
        for flag in ["--render", "--storybook"]:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                build_parser().parse_args(["PROJECT_ID", "--post-production", flag])
        with tempfile.TemporaryDirectory() as directory, patch("obscript.cli.Pipeline") as pipeline:
            for command in ["VIDEO", "new"]:
                with contextlib.redirect_stderr(io.StringIO()) as error:
                    self.assertEqual(main([command, "--post-production", "--vault", directory]), 1)
                self.assertIn("--post-production", error.getvalue())
            pipeline.assert_not_called()

    def test_post_production_resume_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            metadata = create_project(root, parse_command_tokens(["VIDEO"]), Path(directory) / "shared.md")
            with patch("obscript.cli.Pipeline") as pipeline, contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([metadata["id"], "--post-production", "--dry-run", "--vault", directory]), 0)
                pipeline.assert_not_called()
                self.assertIn("validate-production → post-production → verify-post-production", output.getvalue())
                self.assertNotIn("analyze-source", output.getvalue())
            with patch("obscript.cli.Pipeline") as pipeline, contextlib.redirect_stdout(io.StringIO()):
                result = pipeline.return_value.run.return_value
                result.passed_review = True
                result.outputs = []
                self.assertEqual(main([metadata["id"], "--post-production", "--vault", directory]), 0)
                spec = pipeline.return_value.run.call_args.args[0]
                self.assertTrue(spec.post_production)
                self.assertFalse(spec.render)
                self.assertEqual(spec.project_id, metadata["id"])

    def test_storybook_and_render_are_exclusive(self) -> None:
        self.assertTrue(build_parser().parse_args(["VIDEO", "--storybook"]).storybook)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["VIDEO", "--storybook", "--render"])

    def test_default_and_storybook_dry_run_stop_at_requested_phase(self) -> None:
        for flags, ending in [([], "review-script"), (["--storybook"], "validate-storybook")]:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["VIDEO", "--dry-run", *flags]), 0)
            pipeline = output.getvalue().splitlines()[0]
            self.assertTrue(pipeline.endswith(ending))
            self.assertNotIn("produce-video", pipeline)

    def test_resume_cli_retains_original_settings_and_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            saved = parse_command_tokens(["compress", "essay", "VIDEO"], target_duration="8m")
            metadata = create_project(root, saved, Path(directory) / "shared.md")
            with patch("obscript.cli.Pipeline") as pipeline, contextlib.redirect_stdout(io.StringIO()):
                result = pipeline.return_value.run.return_value
                result.passed_review = True
                result.outputs = []
                self.assertEqual(main([metadata["id"], "--storybook", "--output-dir", directory]), 0)
                spec = pipeline.return_value.run.call_args.args[0]
                self.assertEqual(spec.sources, ("VIDEO",))
                self.assertEqual(spec.time_controller, "compress")
                self.assertEqual(spec.format, "essay")
                self.assertEqual(spec.target_duration_seconds, 480)
                self.assertEqual(spec.project_id, metadata["id"])
                self.assertTrue(spec.storybook)
                self.assertFalse(spec.render)
                self.assertEqual(pipeline.call_args.args[0].creative_direction, Path(directory) / "shared.md")
            with patch("obscript.cli.Pipeline") as pipeline, contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([metadata["id"], "--render", "--dry-run", "--output-dir", directory]), 0)
                pipeline.assert_not_called()
                self.assertIn("resume project", output.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([metadata["id"], "--storybook", "--target-duration", "5m", "--output-dir", directory]), 1)

    def test_unknown_project_id_does_not_invoke_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch("obscript.cli.Pipeline") as pipeline:
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(main(["00000000-0000-0000-0000-000000000001", "--render", "--output-dir", directory]), 1)
            self.assertIn("was not found", output.getvalue())
            pipeline.assert_not_called()

    def test_cookie_options(self) -> None:
        args = build_parser().parse_args(["VIDEO", "--cookies-from-browser", "firefox:default"])
        self.assertEqual(args.cookies_from_browser, "firefox:default")
        args = build_parser().parse_args(["VIDEO", "--cookies", "cookies.txt"])
        self.assertEqual(args.cookies, Path("cookies.txt"))
        with patch.dict("os.environ", {"OBSCRIPT_COOKIES_FROM_BROWSER": "chrome"}):
            self.assertEqual(build_parser().parse_args(["VIDEO"]).cookies_from_browser, "chrome")

    def test_rescript_output_root(self) -> None:
        args = build_parser().parse_args(["VIDEO"])
        self.assertEqual(
            args.output_dir,
            Path("/home/zalmo/documents/obsidian/Videos/Videos"),
        )

    def test_shared_creative_direction_follows_vault_and_accepts_override(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["VIDEO", "--vault", "/tmp/other-vault"])
        config = RuntimeConfig(Path("."), args.output_dir, Path("."), Path("ytstt"), Path("codex"),
                               None, "medium", 2, None, False, creative_direction=args.creative_direction)
        self.assertEqual(config.creative_direction_path, Path("/tmp/other-vault/Globals/creative-direction.md"))
        args = parser.parse_args(["VIDEO", "--creative-direction", "/tmp/shared.md"])
        self.assertEqual(args.creative_direction, Path("/tmp/shared.md"))


if __name__ == "__main__":
    unittest.main()
