from __future__ import annotations

import unittest
from pathlib import Path

from obscript.cli import build_parser


class CliDefaultsTests(unittest.TestCase):
    def test_rescript_output_root(self) -> None:
        args = build_parser().parse_args(["VIDEO"])
        self.assertEqual(
            args.output_dir,
            Path("/home/zalmo/documents/obsidian/Videos/Videos"),
        )


if __name__ == "__main__":
    unittest.main()
