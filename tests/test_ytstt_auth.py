from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class FakeDownloadError(Exception):
    pass


class FakeYoutubeDL:
    calls: list = []
    outcomes: list = []

    def __init__(self, params=None, *args, **kwargs):
        self.params = params or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def extract_info(self, url, *args, **kwargs):
        self.calls.append((self.params.copy(), url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class YoutubeAuthTests(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType("yt_dlp")
        fake.YoutubeDL = FakeYoutubeDL
        fake.parse_options = lambda args: types.SimpleNamespace(
            ydl_opts={"cookiesfrombrowser": (args[-1], None, None, None)})
        utils = types.ModuleType("yt_dlp.utils")
        utils.DownloadError = FakeDownloadError
        path = Path(__file__).resolve().parents[1] / "src/obscript/ytstt_auth.py"
        spec = importlib.util.spec_from_file_location("auth_under_test", path)
        self.auth = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"yt_dlp": fake, "yt_dlp.utils": utils}):
            spec.loader.exec_module(self.auth)
        FakeYoutubeDL.calls = []
        FakeYoutubeDL.outcomes = []
        self.auth.configure_auth(argparse.Namespace(cookies=None, cookies_from_browser=None))

    def test_firefox_cookies_on_first_inspection_and_every_playlist_download(self):
        FakeYoutubeDL.outcomes = [{"title": "playlist"}, {"title": "video"}, {"title": "next"}]
        for url, options, download in (
            ("https://www.youtube.com/playlist?list=playlist", {"extract_flat": True}, False),
            ("https://youtu.be/video", {"format": "bestaudio/best"}, True),
            ("https://youtu.be/next", {"format": "bestaudio/best"}, True),
        ):
            with self.auth.YoutubeDL(options) as ydl:
                ydl.extract_info(url, download=download)
            params, actual_url, kwargs = FakeYoutubeDL.calls[-1]
            self.assertEqual(params["cookiesfrombrowser"][0], "firefox")
            self.assertEqual(actual_url, url)
            self.assertEqual(kwargs, {"download": download})
            for key, value in options.items():
                self.assertEqual(params[key], value)
        self.assertEqual(len(FakeYoutubeDL.calls), 3)

    def test_parser_defaults_and_environment_override(self):
        with patch.dict("os.environ", {}, clear=True):
            parser = argparse.ArgumentParser()
            self.auth.add_cookie_arguments(parser)
            self.assertEqual(parser.parse_args([]).cookies_from_browser, "firefox")
        with patch.dict("os.environ", {"OBSCRIPT_COOKIES_FROM_BROWSER": "chrome:Default"}):
            parser = argparse.ArgumentParser()
            self.auth.add_cookie_arguments(parser)
            args = parser.parse_args([])
            self.auth.configure_auth(args)
            self.assertEqual(self.auth.YoutubeDL().params["cookiesfrombrowser"][0], "chrome:Default")
            args = parser.parse_args(["--cookies-from-browser", "firefox:work"])
            self.auth.configure_auth(args)
            self.assertEqual(self.auth.YoutubeDL().params["cookiesfrombrowser"][0], "firefox:work")

    def test_legacy_auto_uses_firefox_immediately(self):
        self.auth.configure_auth(argparse.Namespace(cookies=None, cookies_from_browser="auto"))
        FakeYoutubeDL.outcomes = [{"title": "video"}]
        self.auth.YoutubeDL().extract_info("https://youtu.be/video")
        self.assertEqual(FakeYoutubeDL.calls[0][0]["cookiesfrombrowser"][0], "firefox")

    def test_javascript_runtime_defaults_and_explicit_override(self):
        params = self.auth.YoutubeDL({"quiet": True, "no_warnings": True}).params
        self.assertEqual(params["js_runtimes"], {"deno": {}, "node": {}})
        self.assertFalse(params["no_warnings"])
        self.assertTrue(params["quiet"])
        params = self.auth.YoutubeDL({"js_runtimes": {"deno": {"path": "/custom/deno"}}}).params
        self.assertEqual(params["js_runtimes"], {"deno": {"path": "/custom/deno"}})

    def test_reload_error_explains_solver_dependencies(self):
        def fail():
            raise FakeDownloadError("The page needs to be reloaded.")

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(self.auth.run(fail), 1)
        self.assertIn("yt-dlp[default]", stderr.getvalue())
        self.assertIn("Node 22+", stderr.getvalue())
        self.assertNotIn("refresh the login", stderr.getvalue())

    def test_errors_are_not_retried_anonymously(self):
        for message in ("Video unavailable", "Sign in to confirm you're not a bot",
                        "The page needs to be reloaded."):
            with self.subTest(message=message):
                FakeYoutubeDL.calls = []
                FakeYoutubeDL.outcomes = [FakeDownloadError(message)]
                with self.assertRaises(FakeDownloadError):
                    self.auth.YoutubeDL().extract_info("https://youtu.be/video")
                self.assertEqual(len(FakeYoutubeDL.calls), 1)
                self.assertEqual(FakeYoutubeDL.calls[0][0]["cookiesfrombrowser"][0], "firefox")

    def test_explicit_browser_file_and_opt_out(self):
        with tempfile.TemporaryDirectory() as temporary:
            cookies = Path(temporary) / "cookies.txt"
            cookies.touch()
            for selector, file in (("firefox:work", None), ("none", None), ("firefox", cookies)):
                with self.subTest(selector=selector, file=file):
                    self.auth.configure_auth(argparse.Namespace(cookies=file, cookies_from_browser=selector))
                    params = self.auth.YoutubeDL().params
                    if file:
                        self.assertEqual(params["cookiefile"], str(file))
                        self.assertNotIn("cookiesfrombrowser", params)
                    elif selector == "none":
                        self.assertNotIn("cookiesfrombrowser", params)
                        self.assertNotIn("cookiefile", params)
                    else:
                        self.assertEqual(params["cookiesfrombrowser"][0], selector)

    def test_missing_cookie_file_reports_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "cookies file does not exist"):
                self.auth.configure_auth(argparse.Namespace(
                    cookies=Path(temporary) / "missing.txt", cookies_from_browser=None))


if __name__ == "__main__":
    unittest.main()
