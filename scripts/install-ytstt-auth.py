#!/usr/bin/env python3
"""Install the cookie adapter into an existing ytstt installation, with backup."""
from __future__ import annotations

import argparse
import difflib
import os
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ytstt-home", type=Path,
        default=Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "ytstt",
    )
    parser.add_argument("--apply", action="store_true", help="write changes; default prints the diff")
    args = parser.parse_args()
    target = args.ytstt_home.expanduser() / "ytstt.py"
    original = target.read_text(encoding="utf-8")
    updated = original
    if "from obscript_ytstt_auth import" not in original:
        replacements = (
            ("from yt_dlp import YoutubeDL", "from obscript_ytstt_auth import YoutubeDL, add_cookie_arguments, configure_auth, run"),
            ("    return parser\n", "    add_cookie_arguments(parser)\n    return parser\n"),
            ("    args = build_parser().parse_args()\n", "    args = build_parser().parse_args()\n    configure_auth(args)\n"),
            ("    raise SystemExit(main())", "    raise SystemExit(run(main))"),
        )
        for before, after in replacements:
            if updated.count(before) != 1:
                parser.error(f"unsupported ytstt version: expected one occurrence of {before!r}")
            updated = updated.replace(before, after, 1)
    if not args.apply:
        print("".join(difflib.unified_diff(
            original.splitlines(keepends=True), updated.splitlines(keepends=True),
            fromfile=str(target), tofile=str(target),
        )), end="")
        print(f"Adapter will be installed at {target.parent / 'obscript_ytstt_auth.py'}")
        return
    if updated != original:
        backup = target.with_suffix(".py.before-obscript-auth")
        if backup.exists():
            parser.error(f"refusing to overwrite the existing backup: {backup}")
        shutil.copy2(target, backup)
    adapter = Path(__file__).resolve().parents[1] / "src/obscript/ytstt_auth.py"
    shutil.copy2(adapter, target.parent / "obscript_ytstt_auth.py")
    if updated != original:
        target.write_text(updated, encoding="utf-8")
    print(f"Installed YouTube cookie support at {target.parent}")


if __name__ == "__main__":
    main()
