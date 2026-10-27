from __future__ import annotations

import tempfile
import json
import unittest
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path

from obscript.transcribe import TranscriptionError, _subtitle_to_text, ingest_source


class TranscriptionTests(unittest.TestCase):
    def test_transcription_output_is_logged_instead_of_streamed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "transcriber.py"
            script.write_text(
                "import pathlib, sys\n"
                "print('transcript content')\n"
                "print('download diagnostic', file=sys.stderr)\n"
                "batch = pathlib.Path(sys.argv[sys.argv.index('--output-dir') + 1])\n"
                "output = batch / 'video'\n"
                "output.mkdir()\n"
                "(output / 'transcript.txt').write_text('transcript content')\n"
            )
            transcripts = root / "transcripts"
            transcripts.mkdir()
            assets = ingest_source(str(script), ytstt=Path(sys.executable), transcripts_dir=transcripts)
            self.assertEqual(len(assets), 1)
            log = next(transcripts.glob("*/ytstt.log")).read_text()
            self.assertIn("transcript content", log)
            self.assertIn("download diagnostic", log)

    def test_transcription_failure_points_to_preserved_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "failure.py"
            script.write_text("import sys\nprint('provider error', file=sys.stderr)\nsys.exit(7)\n")
            with self.assertRaises(TranscriptionError) as error:
                ingest_source(str(script), ytstt=Path(sys.executable), transcripts_dir=root)
            log_path = next(root.glob("*/ytstt.log"))
            self.assertIn(str(log_path), str(error.exception))
            self.assertIn("exit code 7", str(error.exception))
            self.assertIn("provider error", log_path.read_text())

    def test_verbose_transcription_inherits_terminal_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch("obscript.transcribe.subprocess.run", side_effect=subprocess.CalledProcessError(3, "ytstt")) as run:
                with self.assertRaisesRegex(TranscriptionError, "terminal output"):
                    ingest_source("VIDEO", ytstt=Path("ytstt"), transcripts_dir=Path(temporary), verbose=True)
            self.assertIsNone(run.call_args.kwargs["stdout"])
            self.assertIsNone(run.call_args.kwargs["stderr"])

    def test_import_retains_individual_video_url_for_visual_references(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "transcript.txt").write_text("Texto")
            (root / "transcript.json").write_text(json.dumps({"title": "Video", "duration": 30,
                "webpage_url": "https://example.com/individual-video"}))
            asset = ingest_source(str(root), ytstt=Path("unused"), transcripts_dir=root / "unused")[0]
            self.assertEqual(asset.original, str(root))
            self.assertEqual(asset.media_source, "https://example.com/individual-video")

    def test_authentication_forwarding(self) -> None:
        for options, expected in (
            ({"cookies_from_browser": "firefox:default"}, ["--cookies-from-browser", "firefox:default"]),
            ({"cookies": Path("cookies.txt")}, ["--cookies", "cookies.txt"]),
            ({}, ["--cookies-from-browser", "firefox"]),
            ({"cookies_from_browser": None}, ["--cookies-from-browser", "firefox"]),
            ({"cookies_from_browser": ""}, ["--cookies-from-browser", "firefox"]),
        ):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temporary:
                def transcribe(command, **kwargs):
                    batch = Path(command[command.index("--output-dir") + 1])
                    output = batch / "video"
                    output.mkdir()
                    (output / "transcript.txt").write_text("a transcript", encoding="utf-8")

                with patch("obscript.transcribe.subprocess.run", side_effect=transcribe) as run:
                    ingest_source("https://youtu.be/video", ytstt=Path("ytstt"),
                                  transcripts_dir=Path(temporary), **options)
                command = run.call_args.args[0]
                self.assertEqual(command[6:], expected)

    def test_subtitle_normalization(self) -> None:
        source = """1
00:00:00,000 --> 00:00:02,000
Primeira frase.

2
00:00:02,000 --> 00:00:04,000
Segunda frase.
"""
        self.assertEqual(_subtitle_to_text(source), "Primeira frase.\n\nSegunda frase.\n")

    def test_direct_text_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            transcript = root / "entrada.txt"
            transcript.write_text("um dois três", encoding="utf-8")
            assets = ingest_source(
                str(transcript),
                ytstt=root / "unused",
                transcripts_dir=root / "transcripts",
            )
            self.assertEqual(len(assets), 1)
            self.assertEqual(assets[0].transcript_txt.read_text(encoding="utf-8"), "um dois três")
            self.assertEqual(assets[0].title, "entrada")


if __name__ == "__main__":
    unittest.main()
