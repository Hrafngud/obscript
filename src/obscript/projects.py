from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from .contracts import ContractError
from .models import CommandSpec
from .storage import read_json, render_script, slugify, unique_directory, write_json, write_yaml


def now() -> str:
    return datetime.now().astimezone().isoformat()


def find_project(output_dir: Path, project_id: str) -> Path | None:
    matches = []
    for path in output_dir.glob("*/project.json"):
        if read_json(path).get("id") == project_id:
            matches.append(path.parent)
    if len(matches) > 1:
        raise ContractError(f"Duplicate project ID {project_id}: {matches}")
    if matches:
        return matches[0]
    # Prevent a mistyped ID from being sent to the transcription backend.
    try:
        UUID(project_id)
    except ValueError:
        if not project_id.startswith("obscript-"):
            return None
    raise ContractError(f"Project {project_id!r} was not found in {output_dir}; use its original --output-dir")


def create_project(root: Path, spec: CommandSpec, direction_path: Path) -> dict:
    command = asdict(spec)
    command.pop("project_id")
    metadata = {
        "schema_version": 1,
        "id": str(uuid4()),
        "created_at": now(),
        "updated_at": now(),
        "phase": "created",
        "status": "running",
        "command": command,
        "creative_direction": str(direction_path),
        "units": {},
    }
    write_json(root / "project.json", metadata)
    return metadata


def create_original_project(output_dir: Path, title: str, spec: CommandSpec,
                            direction_path: Path, *, project_name: str | None = None) -> Path:
    root = unique_directory(output_dir, slugify(project_name or title, "novo-roteiro"))
    metadata = create_project(root, spec, direction_path)
    metadata.update(origin="original", title=title, status="draft")
    write_json(root / "project.json", metadata)
    script = {
        "title": title,
        "thesis": "[Escreva a ideia central ou tese do vídeo.]",
        "metadata": {
            "pipeline": spec.pipeline,
            "time_controller": spec.time_controller,
            "format": spec.format,
            "target_duration_seconds": spec.target_duration_seconds,
        },
        "sections": [
            {"title": heading, "narration": instruction}
            for heading, instruction in [
                ("Gancho", "[Abra com uma pergunta, situação ou ideia que desperte curiosidade.]"),
                ("Introdução", "[Apresente o tema e o que o público vai entender.]"),
                ("Desenvolvimento", "[Desenvolva suas ideias com argumentos e exemplos. Crie outras seções conforme necessário.]"),
                ("Conclusão", "[Retome a ideia central e deixe uma reflexão ou próximo passo.]"),
            ]
        ],
    }
    text = render_script(script)
    text = f"---\nproject_id: {metadata['id']}\norigin: original\nstatus: draft\n" + text[len("---\n"):]
    (root / "script.md").write_text(text, encoding="utf-8")
    write_yaml(root / "run.yaml", {
        "project_id": metadata["id"],
        "created_at": metadata["created_at"],
        "origin": "original",
        **metadata["command"],
        "creative_direction": str(direction_path),
        "agent": None,
    })
    return root


def resume_spec(root: Path, *, storybook: bool, render: bool, post_production: bool = False) -> CommandSpec:
    metadata = read_json(root / "project.json")
    if metadata.get("origin") == "original":
        raise ContractError(f"Original projects are manual drafts; edit {root / 'script.md'}. "
                            "They do not have reviewed structured checkpoints for storybook or rendering.")
    command = dict(metadata["command"])
    command["sources"] = tuple(command["sources"])
    return replace(CommandSpec(**command), storybook=storybook, render=render,
                   post_production=post_production, project_id=metadata["id"])


def update_project(root: Path, *, phase: str | None = None, unit: Path | None = None,
                   status: str = "running", error: str | None = None,
                   creative_direction: Path | None = None) -> None:
    metadata = read_json(root / "project.json")
    if phase:
        if unit is not None:
            metadata["units"][unit.relative_to(root).as_posix()] = phase
            phases = ["created", "transcript", "script", "storybook", "render", "post-production"]
            metadata["phase"] = min(metadata["units"].values(), key=phases.index)
        else:
            metadata["phase"] = phase
    metadata.update(updated_at=now(), status=status)
    if creative_direction is not None:
        metadata["creative_direction"] = str(creative_direction)
    metadata.pop("error", None)
    if error is not None:
        metadata["error"] = error
    write_json(root / "project.json", metadata)
