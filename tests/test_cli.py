from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path

from obscript.cli import build_parser


class CliDefaultsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
