from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from .contracts import ContractError
from .models import CommandSpec
from .storage import read_json, write_json


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


def resume_spec(root: Path, *, storybook: bool, render: bool) -> CommandSpec:
    metadata = read_json(root / "project.json")
    command = dict(metadata["command"])
    command["sources"] = tuple(command["sources"])
    return replace(CommandSpec(**command), storybook=storybook, render=render, project_id=metadata["id"])


def update_project(root: Path, *, phase: str | None = None, unit: Path | None = None,
                   status: str = "running", error: str | None = None,
                   creative_direction: Path | None = None) -> None:
    metadata = read_json(root / "project.json")
    if phase:
        if unit is not None:
            metadata["units"][unit.relative_to(root).as_posix()] = phase
            phases = ["created", "transcript", "script", "storybook", "render"]
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
