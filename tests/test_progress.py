from __future__ import annotations

import contextlib
import io
import os
import unittest
from unittest.mock import patch

from obscript.progress import RunProgress, announce, report, report_project


class Terminal(io.StringIO):
    def isatty(self):
        return True


class RunProgressTests(unittest.TestCase):
    def test_run_details_remain_in_panel_when_phases_and_project_change(self):
        stream = Terminal()
        with patch.dict(os.environ, {"TERM": "xterm"}):
            with RunProgress(stream=stream, agent="Codex", model="test-model", effort="high",
                             project="Creating project..."):
                report_project("my-project-2")
                report("transcribe", "Source 1/2")
                report("storybook-01", "Planning scenes")
        final_panel = stream.getvalue().rsplit("\r\033[2K", 1)[-1].splitlines()
        self.assertEqual(final_panel[:4], ["Agent: Codex", "Model: test-model", "Effort: high",
                                          "Project: my-project-2"])
        self.assertIn("Completed · Storybook planning", final_panel[4])
        self.assertIn("\033[1A", stream.getvalue())
        self.assertEqual(len(final_panel), 5)

    def test_run_details_are_printed_once_in_plain_output(self):
        stream = io.StringIO()
        with RunProgress(stream=stream, agent="OpenCode", model="configured default",
                         effort="configured default", project="my-project"):
            report_project("my-project")
            report("plan-script")
            report("write-script")
        output = stream.getvalue()
        for line in ("Agent: OpenCode", "Model: configured default", "Effort: configured default",
                     "Project: my-project"):
            self.assertEqual(output.count(line), 1)
        self.assertNotIn("\033", output)

    def test_panel_redraws_after_durable_messages_and_survives_failure(self):
        stream = Terminal()
        with patch.dict(os.environ, {"TERM": "xterm"}), contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(RuntimeError):
                with RunProgress(stream=stream, agent="OpenCode", model="provider/model",
                                 effort="configured default", project="my-project"):
                    report("visual-references")
                    announce("Reference warning")
                    report("storybook")
                    raise RuntimeError("failed")
        self.assertEqual(output.getvalue(), "Reference warning\n")
        final_panel = stream.getvalue().rsplit("\r\033[2K", 1)[-1]
        self.assertIn("Agent: OpenCode", final_panel)
        self.assertIn("Model: provider/model", final_panel)
        self.assertIn("Project: my-project", final_panel)
        self.assertIn("Failed · Storybook planning", final_panel)

    def test_live_updates_replace_one_line_and_stop_on_completion(self):
        stream = Terminal()
        with patch.dict(os.environ, {"TERM": "xterm"}):
            with RunProgress(stream=stream) as progress:
                report("transcribe", "Source 1/2")
                report("storybook-01", "Planning scenes")
                self.assertTrue(progress._thread.is_alive())
        output = stream.getvalue()
        self.assertIn("Transcription", output)
        self.assertIn("Storybook planning", output)
        self.assertIn("phase /", output)
        self.assertIn("total", output)
        self.assertIn("\r\033[2K", output)
        self.assertEqual(output.count("\n"), 1)
        self.assertIn("Completed", output)
        self.assertFalse(progress._thread.is_alive())

    def test_failure_and_interrupt_clear_status_and_restore_plain_reporting(self):
        for exception, outcome in [(RuntimeError("failed"), "Failed"), (KeyboardInterrupt(), "Interrupted")]:
            with self.subTest(outcome=outcome), patch.dict(os.environ, {"TERM": "xterm"}):
                stream = Terminal()
                with self.assertRaises(type(exception)):
                    with RunProgress(stream=stream) as progress:
                        report("produce-video-02-of-03")
                        raise exception
                self.assertIn(f"\r\033[2K[obscript] {outcome}", stream.getvalue())
                self.assertFalse(progress._thread.is_alive())
                with contextlib.redirect_stderr(io.StringIO()) as plain:
                    report("review-script")
                self.assertIn("Script review", plain.getvalue())
                self.assertNotIn("\033", plain.getvalue())

    def test_logs_verbose_and_dumb_terminals_have_no_animation(self):
        for stream, verbose, term in [(io.StringIO(), False, "xterm"),
                                      (Terminal(), True, "xterm"), (Terminal(), False, "dumb")]:
            with self.subTest(verbose=verbose, term=term), patch.dict(os.environ, {"TERM": term}):
                with RunProgress(stream=stream, verbose=verbose):
                    report("review-storybook-01")
                    report("review-storybook-01")
                    report("produce-video-02-of-03")
                output = stream.getvalue()
                self.assertNotIn("\033", output)
                self.assertNotIn("\r", output)
                self.assertEqual(output.count("Storybook review"), 1)
                self.assertIn("Rendering video", output)

    def test_long_details_and_control_characters_do_not_wrap_status(self):
        stream = Terminal()
        with patch.dict(os.environ, {"TERM": "xterm"}), \
             patch("obscript.progress.shutil.get_terminal_size", return_value=os.terminal_size((45, 24))):
            with RunProgress(stream=stream):
                report("visual-references", "title\n\r\033[2J" + "x" * 200)
        frames = stream.getvalue().split("\r\033[2K")[1:-1]
        self.assertTrue(frames)
        for frame in frames:
            self.assertLess(len(frame), 45)
            self.assertNotIn("\n", frame)
            self.assertNotIn("\033", frame)

    def test_durable_messages_clear_and_redraw_status(self):
        stream = Terminal()
        with patch.dict(os.environ, {"TERM": "xterm"}), contextlib.redirect_stdout(io.StringIO()) as output:
            with RunProgress(stream=stream):
                report("visual-references")
                announce("Reference warning: details saved in artifact")
                report("storybook")
        self.assertIn("Reference warning", output.getvalue())
        self.assertIn("Storybook planning", stream.getvalue())
