"""Authentication adapter installed beside the workstation's ytstt.py.

Keep retries inside each extraction so playlists never restart transcription.
This module uses ytstt's own yt-dlp installation, not obscript's Python runtime.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from yt_dlp import YoutubeDL as BaseYoutubeDL, parse_options
from yt_dlp.utils import DownloadError


_cookies: dict = {}
_automatic = True


def add_cookie_arguments(parser) -> None:
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument(
        "--cookies-from-browser", metavar="BROWSER[:PROFILE]",
        default=os.environ.get("OBSCRIPT_COOKIES_FROM_BROWSER"),
        help="logged-in browser, auto (default), or none to disable cookie retries",
    )
    auth.add_argument("--cookies", type=Path, metavar="FILE", help="Netscape cookies file")


def configure_auth(args) -> None:
    global _cookies, _automatic
    _cookies = {}
    selector = args.cookies_from_browser or "auto"
    _automatic = not args.cookies and selector == "auto"
    if args.cookies:
        path = args.cookies.expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"cookies file does not exist: {path}")
        _cookies = {"cookiefile": str(path)}
    elif selector not in {"auto", "none"}:
        _cookies = _browser_options(selector)


def _browser_options(selector: str) -> dict:
    # Delegate the complete browser/profile/keyring/container syntax to yt-dlp.
    options = parse_options([
        "--ignore-config", "--cookies-from-browser", selector,
    ]).ydl_opts
    return {"cookiesfrombrowser": options["cookiesfrombrowser"]}


def _detect_browser() -> str | None:
    home = Path.home()
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))
    candidates = (
        ("firefox", home / ".mozilla/firefox"),
        ("firefox", config / "mozilla/firefox"),
        (f"firefox:{home / '.var/app/org.mozilla.firefox/.mozilla/firefox'}",
         home / ".var/app/org.mozilla.firefox/.mozilla/firefox"),
        (f"firefox:{home / 'snap/firefox/common/.mozilla/firefox'}",
         home / "snap/firefox/common/.mozilla/firefox"),
        ("chrome", config / "google-chrome"),
        ("chromium", config / "chromium"),
        ("brave", config / "BraveSoftware/Brave-Browser"),
        ("edge", config / "microsoft-edge"),
        (f"chrome:{home / '.var/app/com.google.Chrome/config/google-chrome'}",
         home / ".var/app/com.google.Chrome/config/google-chrome"),
    )
    return next((selector for selector, path in candidates if path.is_dir()), None)


def _youtube_auth_error(url: str, error: Exception) -> bool:
    host = (urlparse(url).hostname or "").lower()
    youtube = host in {"youtube.com", "youtu.be"} or host.endswith(".youtube.com")
    message = str(error).lower().replace("’", "'")
    return youtube and any(fragment in message for fragment in (
        "sign in to confirm you're not a bot", "sign in to confirm your age",
        "login required", "requires authentication", "only available to registered users",
    ))


class YoutubeDL(BaseYoutubeDL):
    def __init__(self, params=None, *args, **kwargs):
        super().__init__({**(params or {}), **_cookies}, *args, **kwargs)

    def extract_info(self, url, *args, **kwargs):
        global _cookies
        try:
            return super().extract_info(url, *args, **kwargs)
        except DownloadError as exc:
            if not _automatic or self.params.get("cookiesfrombrowser") or self.params.get("cookiefile"):
                raise
            if not _youtube_auth_error(url, exc):
                raise
            browser = _detect_browser()
            if not browser:
                raise DownloadError(
                    "YouTube requires authentication. Sign in in a browser and pass "
                    "--cookies-from-browser BROWSER, or --cookies FILE."
                ) from exc
            print(f"[ytstt] YouTube requires authentication; retrying with {browser} cookies...", flush=True)
            _cookies = _browser_options(browser)
            # A new instance loads a fresh cookie jar; later playlist items reuse
            # the selected authentication options without repeating this retry.
            with BaseYoutubeDL({**self.params, **_cookies}) as authenticated:
                return authenticated.extract_info(url, *args, **kwargs)


def run(main) -> int:
    try:
        return main()
    except (DownloadError, ValueError) as exc:
        print(f"ytstt: {exc}", file=sys.stderr)
        print(
            "For YouTube authentication, sign in and use --cookies-from-browser "
            "firefox (or another browser); refresh the login if cookies are rejected.",
            file=sys.stderr,
        )
        return 1
