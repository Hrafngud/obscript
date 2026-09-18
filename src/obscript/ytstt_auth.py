"""Authentication adapter installed beside the workstation's ytstt.py.

Load browser cookies before URL inspection and every playlist download.
This module uses ytstt's own yt-dlp installation, not obscript's Python runtime.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from yt_dlp import YoutubeDL as BaseYoutubeDL, parse_options
from yt_dlp.utils import DownloadError


_cookies: dict = {}


def add_cookie_arguments(parser) -> None:
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument(
        "--cookies-from-browser", metavar="BROWSER[:PROFILE]",
        default=os.environ.get("OBSCRIPT_COOKIES_FROM_BROWSER") or "firefox",
        help="browser cookies for every request (default: firefox); none disables cookies",
    )
    auth.add_argument("--cookies", type=Path, metavar="FILE", help="Netscape cookies file")


def configure_auth(args) -> None:
    global _cookies
    _cookies = {}
    selector = args.cookies_from_browser or "firefox"
    if args.cookies:
        path = args.cookies.expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"cookies file does not exist: {path}")
        _cookies = {"cookiefile": str(path)}
    elif selector != "none":
        # Keep the old auto selector compatible, but authenticate immediately
        # and use Firefox regardless of other installed browsers.
        _cookies = _browser_options("firefox" if selector == "auto" else selector)


def _browser_options(selector: str) -> dict:
    # Delegate the complete browser/profile/keyring/container syntax to yt-dlp.
    options = parse_options([
        "--ignore-config", "--cookies-from-browser", selector,
    ]).ydl_opts
    return {"cookiesfrombrowser": options["cookiesfrombrowser"]}


class YoutubeDL(BaseYoutubeDL):
    def __init__(self, params=None, *args, **kwargs):
        options = {
            # yt-dlp only enables Deno by default. Workstations with Node
            # also need it enabled to solve YouTube's JavaScript challenges.
            "js_runtimes": {"deno": {}, "node": {}},
            **(params or {}),
            **_cookies,
        }
        # ytstt suppresses warnings, hiding missing runtimes/solver packages
        # behind misleading YouTube reload or authentication errors.
        options["no_warnings"] = False
        super().__init__(options, *args, **kwargs)


def run(main) -> int:
    try:
        return main()
    except (DownloadError, ValueError) as exc:
        print(f"ytstt: {exc}", file=sys.stderr)
        if "the page needs to be reloaded" in str(exc).lower():
            print(
                "YouTube extraction also requires a JavaScript runtime (Node 22+ or Deno 2.3+) "
                "and matching challenge solver scripts. In ytstt's Python environment, run "
                'python -m pip install -U "yt-dlp[default]". '
                "See https://github.com/yt-dlp/yt-dlp/wiki/EJS",
                file=sys.stderr,
            )
        else:
            print(
                "For YouTube authentication, sign in and use --cookies-from-browser "
                "firefox (or another browser); refresh the login if cookies are rejected.",
                file=sys.stderr,
            )
        return 1
