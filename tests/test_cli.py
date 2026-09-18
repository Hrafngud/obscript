from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path

from obscript.cli import build_parser
from obscript.models import RuntimeConfig


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
