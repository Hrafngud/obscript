"""Import authored Markdown without rewriting narration or recording cues."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .contracts import ContractError
from .models import CommandSpec
from .storage import file_sha256, read_json


_TIMESTAMP = r"\d{2}:\d{2}:\d{2}\.\d{3}"
_SECTION_CUE = re.compile(rf"^\*\*[^\n]+ · {_TIMESTAMP} → {_TIMESTAMP}\*\*$")
_SCENE_CUE = re.compile(rf"^### scene-\d+ · {_TIMESTAMP} → {_TIMESTAMP}$")
_PLACEHOLDERS = ("[Escreva a ideia central", "[Abra com uma pergunta", "[Apresente o tema",
                 "[Desenvolva suas ideias", "[Retome a ideia central")


def parse_original_script(path: Path, spec: CommandSpec) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"Cannot read original script at {path}; write your narration there first") from exc
    frontmatter = {}
    if text.startswith("---\n"):
        header, separator, text = text[4:].partition("\n---\n")
        if not separator:
            raise ContractError(f"Unclosed script frontmatter at {path}")
        for line in header.splitlines():
            key, colon, value = line.partition(":")
            if colon:
                frontmatter[key.strip()] = value.strip().strip("\"'")
    try:
        target = int(frontmatter.get("target_duration_seconds", spec.target_duration_seconds or 600))
    except ValueError as exc:
        raise ContractError(f"target_duration_seconds must be a positive integer in {path}") from exc
    format_name = frontmatter.get("format", spec.format)
    controller = frontmatter.get("time_controller", spec.time_controller)
    if target < 1 or format_name not in {"source", "topics", "essay"} or controller not in {"normal", "compress", "extend"}:
        raise ContractError(f"Invalid duration, format, or time_controller in {path}")
    if frontmatter.get("language", "pt-BR") != "pt-BR":
        raise ContractError(f"Original narration must be pt-BR in {path}")
    title = ""
    thesis = []
    sections = []
    body = []

    def finish_section() -> None:
        if sections:
            sections[-1]["narration"] = "\n".join(body).strip()
            body.clear()

    for line in text.splitlines():
        if line.startswith("# ") and not sections:
            title = line[2:].strip()
        elif line.startswith("## "):
            finish_section()
            sections.append({"title": line[3:].strip()})
        elif sections:
            if not _SECTION_CUE.fullmatch(line) and not _SCENE_CUE.fullmatch(line):
                body.append(line)
        elif line.startswith("> "):
            thesis.append(line[2:].strip())
        elif line.strip() and not line.startswith(("**Tempos de referência", "Os intervalos correspondem")):
            raise ContractError(f"Place narration under ## section headings in {path}")
    finish_section()
    if not title or len(sections) < 3 or any(not s["title"] or not s["narration"] for s in sections):
        raise ContractError(f"Original script needs a # title and at least three nonempty ## sections in {path}")
    if any(marker in text for marker in _PLACEHOLDERS):
        raise ContractError(f"Original script still contains template placeholders; finish {path} first")
    if target < len(sections):
        raise ContractError(f"Original script target must allow at least one second per section in {path}")
    weights = [len(s["narration"].split()) for s in sections]
    remaining = target - len(sections)
    accumulated = 0
    for index, section in enumerate(sections):
        previous = accumulated
        accumulated += weights[index]
        heading = section["title"].casefold()
        kind = {"gancho": "hook", "introdução": "introduction", "introducao": "introduction",
                "conclusão": "conclusion", "conclusao": "conclusion"}.get(heading, "body")
        section.update(id=f"section-{index + 1:03d}", type=kind, purpose=section["title"],
                       topic_refs=[f"topic-{index + 1:03d}"],
                       estimated_seconds=1 + remaining * accumulated // sum(weights) - remaining * previous // sum(weights))
    return {"schema_version": "1", "language": "pt-BR", "title": title,
            "thesis": " ".join(thesis) or title,
            "metadata": {"format": format_name, "time_controller": controller, "pipeline": "single",
                         "target_duration_seconds": target}, "sections": sections}


def script_signature(script: dict) -> str:
    # Scene boundaries change whitespace, never the words or their order.
    content = {key: script[key] for key in ("title", "thesis", "metadata")}
    content["sections"] = [{"title": s["title"], "narration": " ".join(s["narration"].split())}
                           for s in script["sections"]]
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def import_original_script(root: Path, spec: CommandSpec) -> tuple[dict, dict]:
    script = parse_original_script(root / "script.md", spec)
    approved_path = root / ".obscript/approved-script.json"
    approved = read_json(approved_path) if approved_path.is_file() else None
    readable_path = root / "script-readable.md"
    if readable_path.is_file() and approved:
        readable = parse_original_script(readable_path, spec)
        baseline = script_signature(approved)
        script_changed = script_signature(script) != baseline
        readable_changed = script_signature(readable) != baseline
        if script_changed and readable_changed and script_signature(script) != script_signature(readable):
            raise ContractError("Both script.md and script-readable.md have conflicting narration edits; synchronize them or edit only one")
        if readable_changed:
            script = readable
    if approved and script_signature(script) == script_signature(approved):
        script = approved  # Retain exact paragraph boundaries and stable section IDs.
    notes = root / "fontes.md"
    inputs = {"script": script_signature(script), "fontes.md": file_sha256(notes) if notes.is_file() else None}
    return script, inputs


def original_context(script: dict, root: Path) -> tuple[dict, dict]:
    sections = script["sections"]
    target = script["metadata"]["target_duration_seconds"]
    topic_ids = [s["topic_refs"][0] for s in sections]
    knowledge = {
        "schema_version": "1", "kind": "single",
        "sources": [{"id": "original-script", "title": script["title"], "source": str(root / "script.md"),
                     "language": "pt-BR", "duration_seconds": target}],
        "summary": {"thesis": script["thesis"], "objective": "Apresentar o roteiro original do autor."},
        "topics": [{"id": topic_id, "title": s["title"], "summary": s["narration"], "facts": [],
                    "arguments": [], "examples": [], "tangents": [], "importance": 1,
                    "source_refs": ["original-script"]} for topic_id, s in zip(topic_ids, sections)],
        "relationships": [], "source_order": topic_ids,
        "narrative": {"format": script["metadata"]["format"], "hook_intent": sections[0]["title"],
                      "conclusion_intent": sections[-1]["title"], "ordered_topic_ids": topic_ids,
                      "transition_intents": []}, "recommended_duration_seconds": target,
    }
    plan = {"schema_version": "1", "title": script["title"], "thesis": script["thesis"],
            "format": script["metadata"]["format"], "time_controller": script["metadata"]["time_controller"],
            "target_duration_seconds": target,
            "hook": {"idea": sections[0]["narration"], "purpose": sections[0]["purpose"],
                     "estimated_seconds": sections[0]["estimated_seconds"]},
            "sections": [{**{key: value for key, value in s.items() if key != "narration"}, "transition": ""}
                         for s in sections]}
    return knowledge, plan
