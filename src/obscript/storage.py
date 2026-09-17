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
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def read_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        return read_json(path)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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


def render_creative_direction(direction: dict) -> str:
    """Render the structured identity without replacing its machine-readable source."""
    labels = {
        "identity": "Identidade", "title": "Título", "visual_thesis": "Tese visual", "audience": "Público", "tone": "Tom",
        "visual_language": "Linguagem visual", "style": "Estilo", "composition": "Composição", "depth": "Profundidade",
        "texture": "Textura", "imagery": "Imagens", "iconography": "Iconografia", "color": "Cor",
        "background": "Fundo", "foreground": "Primeiro plano", "primary": "Primária", "secondary": "Secundária",
        "accent": "Destaque", "semantic_rules": "Regras semânticas", "typography": "Tipografia",
        "display_style": "Títulos", "body_style": "Texto de apoio", "emphasis_style": "Ênfase",
        "casing_rules": "Uso de maiúsculas", "text_density": "Densidade de texto", "motion": "Movimento",
        "overall_energy": "Energia geral", "pacing": "Ritmo", "camera_behavior": "Câmera",
        "entrance_behavior": "Entradas", "exit_behavior": "Saídas", "transition_language": "Transições",
        "emphasis_behavior": "Ênfase em movimento", "layout": "Layout", "safe_area": "Área segura",
        "focal_point_rules": "Ponto focal", "information_hierarchy": "Hierarquia da informação", "whitespace_rules": "Espaço livre",
        "recurring_motifs": "Motivos recorrentes", "id": "Identificador", "description": "Descrição", "usage": "Uso",
        "section_treatment": "Tratamento das seções", "section_type": "Tipo de seção", "visual_behavior": "Comportamento visual",
        "pacing_behavior": "Ritmo da seção", "onscreen_text": "Texto na tela", "purpose": "Objetivo",
        "subtitle_policy": "Legendas", "emphasis_policy": "Política de ênfase",
        "continuity": "Continuidade", "rules": "Regras", "prohibited": "Padrões proibidos",
        "visual_patterns": "Padrões visuais", "motion_patterns": "Padrões de movimento", "text_patterns": "Padrões de texto",
    }
    lines = [f"# {direction['identity']['title']}", ""]

    def render(value: Any, depth: int = 2) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, (dict, list)):
                    lines.extend([f"{'#' * min(depth, 6)} {labels[key]}", ""])
                    render(child, depth + 1)
                else:
                    lines.extend([f"**{labels[key]}:** {child}", ""])
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict):
                    render(child, depth)
                else:
                    lines.append(f"- {child}")
            lines.append("")

    render({key: value for key, value in direction.items() if key != 'schema_version'})
    return "\n".join(lines).rstrip() + "\n"


def render_storybook(storybook: dict, script: dict, *, validation_error: str | None = None) -> str:
    """Render an Obsidian-readable scene plan, including inspectable invalid drafts."""
    status = "invalid" if validation_error is not None else "validated"
    lines = [
        "---", "language: pt-BR", f"status: {status}",
        f"target_duration_seconds: {storybook.get('target_duration_seconds', 0)}", "---", "",
        f"# Storybook · {script['title']}", "",
    ]
    if validation_error is not None:
        lines.extend(["**Rascunho não validado — produção bloqueada.**", "", f"Erro: {validation_error}", ""])
    else:
        lines.extend(["**Plano validado para animações silenciosas.**", ""])
    lines.extend([
        "[Roteiro com tempos](script.md) · [Direção criativa](creative-direction.md)", "",
        "A narração abaixo é referência para gravação humana. As animações seguem os intervalos indicados.", "",
        "## Linha do tempo", "",
        "| Cena | Seção | Início | Fim | Duração | Objetivo visual |",
        "| --- | --- | --- | --- | --- | --- |",
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
            return f"Tempo inválido: {value}"

    scenes = [scene for scene in items(storybook.get("scenes")) if isinstance(scene, dict)]
    for scene in scenes:
        timing = mapping(scene.get("timing"))
        start = timestamp(timing.get("estimated_start_seconds", 0))
        end = timestamp(timing.get("estimated_end_seconds", 0))
        duration = mapping(scene.get("voiceover")).get("estimated_seconds", "—")
        lines.append(f"| {cell(scene.get('id', '—'))} | {cell(scene.get('script_section_id', '—'))} | {start} | {end} | {duration} s | {cell(scene.get('visual_goal', '—'))} |")
    lines.append("")
    sections = {section["id"]: section["title"] for section in script["sections"]}
    for scene in scenes:
        timing = mapping(scene.get("timing"))
        start = timestamp(timing.get("estimated_start_seconds", 0))
        end = timestamp(timing.get("estimated_end_seconds", 0))
        section_id = str(scene.get("script_section_id", "—"))
        voiceover = mapping(scene.get("voiceover"))
        lines.extend([
            f"## {scene.get('id', 'Cena')} · {start} → {end}", "",
            f"**Seção:** {section_id} · {sections.get(section_id, 'Seção desconhecida')}", "",
            f"**Duração:** {voiceover.get('estimated_seconds', '—')} s", "",
            f"**Momento narrativo:** {scene.get('narrative_beat', '—')}", "",
            f"**Objetivo visual:** {scene.get('visual_goal', '—')}", "",
            "### Narração de referência", "", voiceover.get("text", "—"), "",
            "### Composição", "",
        ])
        composition = mapping(scene.get("composition"))
        for key, label in [("layout", "Layout"), ("focal_element", "Elemento focal")]:
            lines.extend([f"**{label}:** {composition.get(key, '—')}", ""])
        for element in items(composition.get("supporting_elements")):
            lines.append(f"- {element}")
        lines.extend(["", "### Elementos visuais", ""])
        for element in items(scene.get("visual_elements")):
            element = mapping(element)
            lines.extend([f"- **{element.get('type', '—')}:** {element.get('content', '—')} — {element.get('role', '—')}"])
        lines.extend(["", "### Texto na tela", ""])
        blocks = items(scene.get("onscreen_text"))
        if not blocks:
            lines.append("Nenhum.")
        for block in blocks:
            block = mapping(block)
            lines.append(f"- {block.get('text', '—')} — {block.get('purpose', '—')}")
        lines.extend(["", "### Animação", ""])
        animation = mapping(scene.get("animation"))
        for key, label in [("entrance", "Entrada"), ("continuous", "Movimento contínuo"),
                           ("emphasis", "Ênfase"), ("exit", "Saída"), ("camera", "Câmera")]:
            lines.extend([f"**{label}:** {animation.get(key, '—')}", ""])
        lines.extend(["### Transição para a próxima cena", "", scene.get("transition_out", "—"), "",
                      "### Recursos necessários", ""])
        assets = items(scene.get("asset_requirements"))
        if not assets:
            lines.append("Nenhum recurso externo.")
        for asset in assets:
            asset = mapping(asset)
            lines.append(f"- **{asset.get('type', '—')}:** {asset.get('description', '—')}")
        lines.extend(["", "### Instrução de produção", "", scene.get("render_brief", "—"), ""])
    return "\n".join(str(line) for line in lines).rstrip() + "\n"
