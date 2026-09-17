from __future__ import annotations

import argparse
import importlib.util
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
        self.auth.configure_auth(argparse.Namespace(cookies=None, cookies_from_browser="auto"))

    def test_retry_and_reuse_for_playlist_download(self):
        FakeYoutubeDL.outcomes = [FakeDownloadError("Sign in to confirm you’re not a bot"),
                                  {"title": "video"}, {"title": "next"}]
        with patch.object(self.auth, "_detect_browser", return_value="firefox"):
            with self.auth.YoutubeDL({"extract_flat": True}) as ydl:
                self.assertEqual(ydl.extract_info("https://www.youtube.com/watch?v=video", download=False),
                                 {"title": "video"})
            with self.auth.YoutubeDL({"format": "bestaudio/best"}) as ydl:
                ydl.extract_info("https://youtu.be/next", download=True)
        first, retry, following = FakeYoutubeDL.calls
        self.assertNotIn("cookiesfrombrowser", first[0])
        self.assertEqual(retry[0]["cookiesfrombrowser"][0], "firefox")
        self.assertTrue(retry[0]["extract_flat"])
        self.assertEqual(retry[2], {"download": False})
        self.assertEqual(following[0]["cookiesfrombrowser"][0], "firefox")
        self.assertEqual(following[2], {"download": True})

    def test_firefox_is_preferred_when_chrome_is_also_installed(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            (home / ".mozilla/firefox").mkdir(parents=True)
            (home / ".config/google-chrome").mkdir(parents=True)
            with patch.object(self.auth.Path, "home", return_value=home), patch.dict(
                "os.environ", {"XDG_CONFIG_HOME": str(home / ".config")}
            ):
                self.assertEqual(self.auth._detect_browser(), "firefox")

    def test_flatpak_firefox_is_preferred_over_chrome(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            profile = home / ".var/app/org.mozilla.firefox/.mozilla/firefox"
            profile.mkdir(parents=True)
            (home / ".config/google-chrome").mkdir(parents=True)
            with patch.object(self.auth.Path, "home", return_value=home), patch.dict(
                "os.environ", {"XDG_CONFIG_HOME": str(home / ".config")}
            ):
                self.assertEqual(self.auth._detect_browser(), f"firefox:{profile}")

    def test_unrelated_errors_are_not_retried(self):
        for url, message in (("https://youtu.be/video", "Video unavailable"),
                             ("https://example.com/video", "Sign in to confirm you're not a bot")):
            with self.subTest(url=url):
                FakeYoutubeDL.calls = []
                FakeYoutubeDL.outcomes = [FakeDownloadError(message)]
                with self.assertRaises(FakeDownloadError):
                    self.auth.YoutubeDL().extract_info(url)
                self.assertEqual(len(FakeYoutubeDL.calls), 1)

    def test_explicit_authentication_and_opt_out_do_not_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            cookies = Path(temporary) / "cookies.txt"
            cookies.touch()
            for selector, file in (("firefox", None), ("none", None), ("auto", cookies)):
                with self.subTest(selector=selector, file=file):
                    self.auth.configure_auth(argparse.Namespace(cookies=file, cookies_from_browser=selector))
                    FakeYoutubeDL.calls = []
                    FakeYoutubeDL.outcomes = [FakeDownloadError("Sign in to confirm you're not a bot")]
                    with self.assertRaises(FakeDownloadError):
                        self.auth.YoutubeDL().extract_info("https://youtu.be/video")
                    self.assertEqual(len(FakeYoutubeDL.calls), 1)
                    params = FakeYoutubeDL.calls[0][0]
                    if file:
                        self.assertEqual(params["cookiefile"], str(file))
                    elif selector == "firefox":
                        self.assertEqual(params["cookiesfrombrowser"][0], "firefox")

    def test_retry_is_bounded_and_missing_browser_is_actionable(self):
        for browser in (None, "chrome"):
            with self.subTest(browser=browser):
                self.auth.configure_auth(argparse.Namespace(cookies=None, cookies_from_browser="auto"))
                FakeYoutubeDL.calls = []
                FakeYoutubeDL.outcomes = [FakeDownloadError("Sign in to confirm you're not a bot")] * 2
                with patch.object(self.auth, "_detect_browser", return_value=browser):
                    with self.assertRaises(FakeDownloadError):
                        self.auth.YoutubeDL().extract_info("https://youtu.be/video")
                self.assertEqual(len(FakeYoutubeDL.calls), 2 if browser else 1)


if __name__ == "__main__":
    unittest.main()
