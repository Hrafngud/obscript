from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ORIGINAL = """from yt_dlp import YoutubeDL
def build_parser():
    return parser
def main():
    args = build_parser().parse_args()
if __name__ == '__main__':
    raise SystemExit(main())
"""


class InstallAuthTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "scripts/install-ytstt-auth.py"
        spec = importlib.util.spec_from_file_location("installer_under_test", path)
        self.installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.installer)

    def test_dependency_install_uses_ytstt_environment_and_reapply_keeps_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            target = home / "ytstt.py"
            target.write_text(ORIGINAL)
            python = home / ".venv/bin/python"
            python.parent.mkdir(parents=True)
            python.touch()
            args = ["installer", "--ytstt-home", str(home), "--apply", "--install-dependencies"]
            with patch("sys.argv", args), patch.object(self.installer.subprocess, "run") as run:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.installer.main()
                    self.installer.main()
            self.assertEqual(run.call_count, 2)
            run.assert_called_with(
                [str(python), "-m", "pip", "install", "--upgrade", "yt-dlp[default]"], check=True)
            self.assertIn("configure_auth(args)", target.read_text())
            self.assertEqual(target.with_suffix(".py.before-obscript-auth").read_text(), ORIGINAL)
            self.assertEqual((home / "obscript_ytstt_auth.py").read_text(),
                             (Path(__file__).resolve().parents[1] / "src/obscript/ytstt_auth.py").read_text())

    def test_dry_run_never_installs_dependencies_or_writes_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            target = home / "ytstt.py"
            target.write_text(ORIGINAL)
            for flags in ([], ["--install-dependencies"]):
                with patch("sys.argv", ["installer", "--ytstt-home", str(home), *flags]):
                    with patch.object(self.installer.subprocess, "run") as run:
                        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                            if flags:
                                with self.assertRaises(SystemExit):
                                    self.installer.main()
                            else:
                                self.installer.main()
                        run.assert_not_called()
                self.assertEqual(list(home.iterdir()), [target])
                self.assertEqual(target.read_text(), ORIGINAL)

    def test_dependency_failure_leaves_existing_installation_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            target = home / "ytstt.py"
            target.write_text(ORIGINAL)
            python = home / ".venv/bin/python"
            python.parent.mkdir(parents=True)
            python.touch()
            args = ["installer", "--ytstt-home", str(home), "--apply", "--install-dependencies"]
            with patch("sys.argv", args), patch.object(self.installer.subprocess, "run",
                                                       side_effect=subprocess.CalledProcessError(1, "pip")):
                with self.assertRaises(subprocess.CalledProcessError):
                    self.installer.main()
            self.assertEqual(target.read_text(), ORIGINAL)
            self.assertFalse(target.with_suffix(".py.before-obscript-auth").exists())
            self.assertFalse((home / "obscript_ytstt_auth.py").exists())


if __name__ == "__main__":
    unittest.main()
