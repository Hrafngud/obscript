from __future__ import annotations

import json
import hashlib
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any

from .contracts import ContractError


def read_creative_direction(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"Cannot read shared creative direction at {path}; create it or pass --creative-direction FILE") from exc
    if not content.strip():
        raise ContractError(f"Shared creative direction is empty: {path}; add standards or suggested fields")
    return content


def creative_direction_reference(path: Path, content: str) -> dict:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}


def slugify(value: str, fallback: str = "video") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug[:80] or fallback


def unique_directory(parent: Path, name: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    candidate = parent / name
    suffix = 2
    while candidate.exists():
        candidate = parent / f"{name}-{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid JSON at {path}: {exc}") from exc


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_yaml(path: Path, data: Any) -> None:
    try:
        import yaml  # type: ignore

        content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    except ImportError:
        # JSON is valid YAML 1.2 and keeps the CLI dependency-free.
        content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def read_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        return read_json(path)
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContractError(f"Invalid YAML at {path}: {exc}") from exc


def copy_if_present(source: Path | None, destination: Path) -> Path | None:
    if source is None or not source.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def render_plan(plan: dict) -> str:
    lines = [f"# {plan['title']}", "", f"**Tese:** {plan['thesis']}", ""]
    lines.extend(
        [
            f"**Formato:** {plan['format']}",
            f"**Duração-alvo:** {plan['target_duration_seconds']} s",
            "",
            "## Gancho",
            "",
            plan["hook"]["idea"],
            "",
        ]
    )
    for section in plan["sections"]:
        lines.extend(
            [
                f"## {section['title']}",
                "",
                f"- Tipo: {section['type']}",
                f"- Objetivo: {section['purpose']}",
                f"- Duração estimada: {section['estimated_seconds']} s",
                f"- Tópicos: {', '.join(section['topic_refs']) or '—'}",
                f"- Transição: {section['transition'] or '—'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def format_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remaining = divmod(milliseconds, 3_600_000)
    minutes, remaining = divmod(remaining, 60_000)
    secs, millis = divmod(remaining, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def render_script(script: dict, storybook: dict | None = None) -> str:
    metadata = script["metadata"]
    lines = [
        "---",
        "language: pt-BR",
        f"pipeline: {metadata['pipeline']}",
        f"time_controller: {metadata['time_controller']}",
        f"format: {metadata['format']}",
        f"target_duration_seconds: {metadata['target_duration_seconds']}",
        "---",
        "",
        f"# {script['title']}",
        "",
        f"> {script['thesis']}",
        "",
    ]
    if storybook is not None:
        lines.extend([
            "**Tempos de referência para a gravação humana da narração.**",
            "Os intervalos correspondem às cenas da animação; as marcações não fazem parte da fala.", "",
        ])
    for section in script["sections"]:
        lines.extend([f"## {section['title']}", ""])
        if storybook is None:
            lines.extend([section["narration"].strip(), ""])
            continue
        scenes = [scene for scene in storybook["scenes"] if scene["script_section_id"] == section["id"]]
        section_start = format_timestamp(scenes[0]["timing"]["estimated_start_seconds"])
        section_end = format_timestamp(scenes[-1]["timing"]["estimated_end_seconds"])
        lines.extend([f"**{section['id']} · {section_start} → {section_end}**", ""])
        for scene in scenes:
            start = format_timestamp(scene["timing"]["estimated_start_seconds"])
            end = format_timestamp(scene["timing"]["estimated_end_seconds"])
            lines.extend([f"### {scene['id']} · {start} → {end}", "", scene["voiceover"]["text"].strip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def render_storybook(storybook: dict, script: dict, *, direction_path: Path | None = None, validation_error: str | None = None) -> str:
    """Render an Obsidian-readable scene plan, including inspectable invalid drafts."""
    status = "invalid" if validation_error is not None else "validated"
    lines = [
        "---", "language: en", f"status: {status}",
        f"target_duration_seconds: {storybook.get('target_duration_seconds', 0)}", "---", "",
        f"# Storybook · {script['title']}", "",
    ]
    if validation_error is not None:
        lines.extend(["**Unvalidated draft — production blocked.**", "", f"Error: {validation_error}", ""])
    else:
        lines.extend(["**Validated plan for silent animations.**", ""])
    direction_link = ""
    if direction_path is not None:
        # The caller supplies a path relative to the document for Obsidian links.
        direction_link = f" · [Shared creative direction](<{direction_path.as_posix()}>)"
    lines.extend([
        f"[Readable script](script-readable.md) · [Script with timestamps](script.md){direction_link}", "",
        "Scene directions are in English; narration and on-screen labels retain their original language.", "",
        "[Structured production plan](storybook.yaml) contains the exact narration references and all scene fields.", "",
        "## Timeline", "",
        "| Scene | Section | Start | End | Duration |",
        "| --- | --- | --- | --- | --- |",
    ])

    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    def mapping(value: Any) -> dict:
        return value if isinstance(value, dict) else {}

    def items(value: Any) -> list:
        return value if isinstance(value, list) else []

    def timestamp(value: Any) -> str:
        try:
            return format_timestamp(float(value))
        except (ValueError, TypeError, OverflowError):
            return f"Invalid time: {value}"

    scenes = [scene for scene in items(storybook.get("scenes")) if isinstance(scene, dict)]
    for scene in scenes:
        timing = mapping(scene.get("timing"))
        start = timestamp(timing.get("estimated_start_seconds", 0))
        end = timestamp(timing.get("estimated_end_seconds", 0))
        duration = mapping(scene.get("voiceover")).get("estimated_seconds", "—")
        lines.append(f"| {cell(scene.get('id', '—'))} | {cell(scene.get('script_section_id', '—'))} | {start} | {end} | {duration} s |")
    lines.append("")
    sections = {section["id"]: section["title"] for section in script["sections"]}
    for scene in scenes:
        timing = mapping(scene.get("timing"))
        start = timestamp(timing.get("estimated_start_seconds", 0))
        end = timestamp(timing.get("estimated_end_seconds", 0))
        section_id = str(scene.get("script_section_id", "—"))
        voiceover = mapping(scene.get("voiceover"))
        lines.extend([
            f"## {scene.get('id', 'Scene')} · {start} → {end}", "",
            f"**Section:** {section_id} · {sections.get(section_id, 'Unknown section')}", "",
            f"**Duration:** {voiceover.get('estimated_seconds', '—')} s", "",
            "### Scene", "",
            "**Layout:**", "", scene.get("render_brief", "—"), "",
        ])
    if validation_error is not None:
        lines.extend(["## Invalid structured draft", "", "```json",
                      json.dumps(storybook, ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(str(line) for line in lines).rstrip() + "\n"
