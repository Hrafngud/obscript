from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from obscript.transcribe import _subtitle_to_text, ingest_source


class TranscriptionTests(unittest.TestCase):
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
