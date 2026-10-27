from __future__ import annotations

import contextlib
import io
import json
import os
import shlex
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from obscript import hyperframes_runtime as runtime
from obscript.production import ProductionAgent, ProductionError, hyperframes_handoff
from test_visual_production import config_fixture


class SharedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.shared = self.root / "shared runtime"
        self.env = patch.dict(os.environ, {"OBSCRIPT_HYPERFRAMES_HOME": str(self.shared)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def install_fixture(self, directory=None, version=runtime.HYPERFRAMES_VERSION, ready=True):
        package = (directory or self.shared) / "node_modules/hyperframes"
        (package / "bin").mkdir(parents=True, exist_ok=True)
        (package / "bin/hyperframes.mjs").write_text("// CLI fixture")
        (package / "dist/studio").mkdir(parents=True, exist_ok=True)
        (package / "dist/studio/index.html").write_text("Studio fixture")
        (package / "package.json").write_text(json.dumps({
            "version": version, "bin": {"hyperframes": "./bin/hyperframes.mjs"},
        }))
        if ready:
            (package.parents[1] / ".ready").write_text(version)
        return package / "bin/hyperframes.mjs"

    def test_projects_and_stages_share_one_install(self):
        def install(*args, **kwargs):
            self.install_fixture(ready=False)
            return subprocess.CompletedProcess([], 0, "installed", "")
        with patch.object(runtime.subprocess, "run", side_effect=install) as run:
            first = runtime.ensure_runtime()
            second = runtime.ensure_runtime()
        self.assertEqual(first, second)
        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertIn(f"hyperframes@{runtime.HYPERFRAMES_VERSION}", command)
        self.assertEqual(command[command.index("--prefix") + 1], str(self.shared))
        self.assertEqual(run.call_args.kwargs["cwd"], self.shared)
        handoffs = [hyperframes_handoff(self.root / stage, 10, "message", "audience")
                    for stage in ("project-a/production", "project-a/post-production", "project-b/production")]
        self.assertEqual(len({handoff["runtime"]["directory"] for handoff in handoffs}), 1)
        self.assertEqual(len({handoff["project_directory"] for handoff in handoffs}), 3)
        self.assertTrue(all(handoff["runtime"]["command"] == [str(runtime.LAUNCHER)] for handoff in handoffs))

    def test_concurrent_setup_installs_only_once(self):
        installing = threading.Event()
        release = threading.Event()
        def install(*args, **kwargs):
            self.install_fixture(ready=False)
            installing.set()
            self.assertTrue(release.wait(5))
            return subprocess.CompletedProcess([], 0, "installed", "")
        with patch.object(runtime.subprocess, "run", side_effect=install) as run:
            with ThreadPoolExecutor(max_workers=2) as workers:
                first = workers.submit(runtime.ensure_runtime)
                self.assertTrue(installing.wait(5))
                second = workers.submit(runtime.ensure_runtime)
                release.set()
                self.assertEqual(first.result(), second.result())
        run.assert_called_once()

    def test_failed_install_is_logged_and_retryable(self):
        with patch.object(runtime.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "network failed")):
            with self.assertRaisesRegex(runtime.HyperframesRuntimeError, "install.log"):
                runtime.ensure_runtime()
        self.assertIn("network failed", (self.shared / "install.log").read_text())
        self.install_fixture()
        with patch.object(runtime.subprocess, "run") as run:
            runtime.ensure_runtime()
        run.assert_not_called()

    def test_incomplete_or_wrong_version_install_is_not_reused(self):
        cli = self.install_fixture(version="0.0.1")
        self.assertIsNone(runtime._installed_cli(self.shared))
        self.install_fixture()
        studio = cli.parents[1] / "dist/studio/index.html"
        studio.unlink()
        self.assertIsNone(runtime._installed_cli(self.shared))
        self.install_fixture()
        cli.unlink()
        self.assertIsNone(runtime._installed_cli(self.shared))

    def test_default_location_respects_xdg_cache(self):
        with patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.root / "cache")}, clear=True):
            self.assertEqual(runtime.runtime_directory(), self.root / "cache/obscript/hyperframes")

    def test_init_uses_shared_cli_and_rewrites_generated_scripts(self):
        cli = self.install_fixture()
        project = self.root / "composition with spaces"
        def scaffold(command, **kwargs):
            self.assertEqual(command, ["node", str(cli), "init", str(project), "--non-interactive"])
            project.mkdir()
            (project / "index.html").write_text("composition")
            (project / "package.json").write_text(json.dumps({
                "scripts": {"check": "npx --yes hyperframes@0.0.1 check --strict", "custom": "echo hyperframes"},
                "devDependencies": {"hyperframes": "^0.0.1", "gsap": "3.12.5"},
            }))
            return subprocess.CompletedProcess(command, 0)
        with patch.object(runtime.subprocess, "run", side_effect=scaffold):
            self.assertEqual(runtime.main(["init", str(project), "--non-interactive"]), 0)
        data = json.loads((project / "package.json").read_text())
        self.assertEqual(shlex.split(data["scripts"]["check"]), [str(runtime.LAUNCHER), "check", "--strict"])
        self.assertEqual(data["scripts"]["custom"], "echo hyperframes")
        self.assertEqual(data["devDependencies"], {"gsap": "3.12.5"})
        self.assertFalse((project / "node_modules").exists())
        self.assertIn(str(runtime.LAUNCHER), (project / "AGENTS.md").read_text())
        runtime.prepare_project(project)
        self.assertEqual(data, json.loads((project / "package.json").read_text()))
        self.assertEqual((project / "AGENTS.md").read_text().count(runtime.PROJECT_NOTICE_START), 1)

    def test_render_keeps_project_cwd_arguments_and_exit_code(self):
        cli = self.install_fixture()
        args = ["render", "--output", "a file.mp4"]
        with patch.object(runtime.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)) as run:
            self.assertEqual(runtime.main(args), 7)
        run.assert_called_once_with(["node", str(cli), *args], check=False)

    def test_failed_init_does_not_modify_existing_project(self):
        self.install_fixture()
        project = self.root / "existing"
        project.mkdir()
        (project / "AGENTS.md").write_text("Existing instructions")
        with patch.object(runtime.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
            self.assertEqual(runtime.main(["init", str(project)]), 1)
        self.assertEqual((project / "AGENTS.md").read_text(), "Existing instructions")

    def test_runtime_setup_failure_never_launches_agent(self):
        output = self.root / "production"
        output.mkdir()
        agent = ProductionAgent(config_fixture(self.root), self.root)
        with patch("obscript.production.ensure_runtime", side_effect=runtime.HyperframesRuntimeError("install failed")), \
                patch("obscript.production.subprocess.run") as run:
            with self.assertRaisesRegex(ProductionError, "install failed"):
                agent._execute("produce-video", self.root / "request.json", output)
        run.assert_not_called()

    def test_upgrade_does_not_spawn_another_install(self):
        self.install_fixture()
        with patch.object(runtime.subprocess, "run") as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(runtime.main(["upgrade", "--project", "."]), 1)
        run.assert_not_called()
