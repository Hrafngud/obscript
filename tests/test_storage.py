from __future__ import annotations

import unittest

from obscript.storage import render_script, slugify


class StorageTests(unittest.TestCase):
    def test_slugify_pt_br(self) -> None:
        self.assertEqual(slugify("A Ilusão da Programação"), "a-ilusao-da-programacao")

    def test_script_markdown(self) -> None:
        text = render_script(
            {
                "title": "Título",
                "thesis": "Tese",
                "metadata": {
                    "pipeline": "single",
                    "time_controller": "normal",
                    "format": "source",
                    "target_duration_seconds": 60,
                },
                "sections": [{"title": "Gancho", "narration": "Você já percebeu isso?"}],
            }
        )
        self.assertIn("language: pt-BR", text)
        self.assertIn("# Título", text)
        self.assertIn("## Gancho", text)


if __name__ == "__main__":
    unittest.main()
