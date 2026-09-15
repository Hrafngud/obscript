from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any


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
    return json.loads(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: Any) -> None:
    try:
        import yaml  # type: ignore

        content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    except ImportError:
        # JSON is valid YAML 1.2 and keeps the CLI dependency-free.
        content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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


def render_script(script: dict) -> str:
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
    for section in script["sections"]:
        lines.extend(
            [
                f"## {section['title']}",
                "",
                section["narration"].strip(),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
