"""Apply human edits in the readable storybook to the render plan."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from urllib.parse import unquote

from .asset_refs import ASSET_LIBRARY_ROOT, resolve_asset_links
from .contracts import ContractError


SCENE_HEADING = re.compile(r"^## (scene-\d{3,})\b.*$", re.MULTILINE)
ASSET_LINK = re.compile(r"\[([^\]]+)\]\((file:///\{ref-root\}/Globals/assets/[^)]+)\)")
ABSOLUTE_ASSET = re.compile(re.escape(str(ASSET_LIBRARY_ROOT)) + r"/[^\s)\],;]+")
RASTER_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}


def _sections(markdown: str) -> tuple[dict[str, str], str]:
    matches = list(SCENE_HEADING.finditer(markdown))
    scenes: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[match.end():end]
        layout = re.search(r"^\*\*Layout:\*\*\s*\n", body, re.MULTILINE)
        if layout:
            scenes[match.group(1)] = body[layout.end():].strip()
    shared = re.search(r"^## Shared visual system\s*\n(.*?)(?=^## |\Z)", markdown,
                       re.MULTILINE | re.DOTALL)
    return scenes, shared.group(1).strip() if shared else ""


def _selected_assets(layout: str) -> list[dict[str, str]]:
    labels = {}
    for label, url in ASSET_LINK.findall(layout):
        path = resolve_asset_links(url)
        labels[path] = label
    resolved = resolve_asset_links(layout)
    for match in ABSOLUTE_ASSET.finditer(resolved):
        path = match.group().rstrip(".,:;")
        labels.setdefault(path, Path(path).stem)
    selected = []
    for path, label in labels.items():
        asset = Path(unquote(path))
        if not asset.resolve().is_relative_to(ASSET_LIBRARY_ROOT.resolve()) or not asset.is_file():
            raise ContractError(f"Readable storybook selects a missing or external asset: {path}")
        background = "/background1/" in path and asset.suffix.lower() in RASTER_EXTENSIONS
        selected.append({"path": path, "usage": "background" if background else "foreground",
                         "semantic_role": f"Manual storybook selection: {label}"})
    return selected


def apply_readable_storybook(storybook: dict, markdown: str, baseline_markdown: str) -> tuple[dict, str, bool]:
    """Merge changed Layout paragraphs; return effective plan and shared human direction."""
    layouts, shared = _sections(markdown)
    baseline_layouts, baseline_shared = _sections(baseline_markdown)
    result = copy.deepcopy(storybook)
    changed = False
    for scene in result["scenes"]:
        scene_id = scene["id"]
        if scene_id not in layouts or layouts[scene_id] == baseline_layouts.get(scene_id):
            continue
        layout = layouts[scene_id]
        if not layout:
            raise ContractError(f"{scene_id}: readable storybook Layout is empty")
        selected = _selected_assets(layout)
        old_paths = {asset["path"] for asset in scene["design_pillars"]["assets"]["selected_assets"]}
        scene["render_brief"] = resolve_asset_links(layout)
        scene["composition"]["layout"] = scene["render_brief"]
        plan = scene["design_pillars"]["assets"]
        plan["selected_assets"] = selected
        plan["exception_reason"] = "" if any(asset["usage"] == "foreground" for asset in selected) else (
            "The manually revised scene intentionally uses no library foreground asset."
        )
        for asset in selected:
            if asset["path"] not in plan["candidates_considered"]:
                plan["candidates_considered"].append(asset["path"])
        scene["visual_elements"] = [item for item in scene["visual_elements"]
                                    if not any(path in item["content"] for path in old_paths)]
        scene["asset_requirements"] = [item for item in scene["asset_requirements"]
                                       if not any(path in item["description"] for path in old_paths)]
        for asset in selected:
            scene["visual_elements"].append({"type": asset["usage"] + " asset", "content": asset["path"],
                                             "role": asset["semantic_role"]})
            scene["asset_requirements"].append({"type": asset["usage"] + " asset",
                                                "description": f"{asset['path']}; {asset['semantic_role']}"})
        changed = True
    return result, shared, changed or shared != baseline_shared
