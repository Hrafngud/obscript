"""Translate Obsidian preview links into paths usable by production."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote, unquote

from .contracts import ContractError


ASSET_LIBRARY_ROOT = Path("/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets")
OBSIDIAN_ASSET_PREFIX = "file:///{ref-root}/Globals/assets/"
_ASSET_LINK = re.compile(r"\[(?:\\.|[^\]])*\]\((file:///\{ref-root\}/Globals/assets/[^)]+)\)")
_ASSET_URL = re.compile(r"file:///\{ref-root\}/Globals/assets/[^\s)]+")


def _asset_path(url: str) -> str:
    relative = Path(unquote(url.removeprefix(OBSIDIAN_ASSET_PREFIX)))
    path = (ASSET_LIBRARY_ROOT / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(ASSET_LIBRARY_ROOT.resolve()):
        raise ContractError(f"Obsidian asset link escapes the library: {url}")
    return str(path)


def resolve_asset_links(value):
    """Return a copy with preview links replaced by absolute library paths."""
    if isinstance(value, dict):
        return {key: resolve_asset_links(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_asset_links(item) for item in value]
    if not isinstance(value, str):
        return value
    result = _ASSET_LINK.sub(lambda match: _asset_path(match.group(1)), value)
    result = _ASSET_URL.sub(lambda match: _asset_path(match.group()), result)
    if OBSIDIAN_ASSET_PREFIX in result:
        raise ContractError(f"Invalid Obsidian asset link: {result}")
    return result


def preview_asset_link(path: str) -> str | None:
    """Create the link format used by the Obsidian image preview extension."""
    absolute = Path(path)
    if not absolute.is_absolute():
        return None
    try:
        relative = absolute.relative_to(ASSET_LIBRARY_ROOT)
    except ValueError:
        return None
    label = absolute.stem.replace("[", "\\[").replace("]", "\\]")
    return f"[{label}]({OBSIDIAN_ASSET_PREFIX}{quote(relative.as_posix(), safe='/')})"


def preview_asset_text(text: str, paths: list[str]) -> str:
    """Link selected scene assets in readable prose without changing the plan."""
    result = resolve_asset_links(text)
    for path in sorted(set(paths), key=len, reverse=True):
        link = preview_asset_link(path)
        if link:
            result = result.replace(path, link)
    return result
