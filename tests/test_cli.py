from __future__ import annotations

import unittest
import contextlib
import io
import tempfile
from unittest.mock import patch
from pathlib import Path

from obscript.cli import build_parser, main
from obscript.contracts import parse_command_tokens
from obscript.projects import create_project
from obscript.models import RuntimeConfig


class CliDefaultsTests(unittest.TestCase):
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
