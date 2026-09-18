from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandSpec:
    pipeline: str
    time_controller: str
    format: str
    sources: tuple[str, ...]
    target_duration_seconds: int | None = None
    split_count: int | None = None
    render: bool = False
    storybook: bool = False
    project_id: str | None = None


@dataclass(frozen=True)
class SourceAsset:
    original: str
    title: str
    transcript_txt: Path
    transcript_srt: Path | None
    transcript_json: Path | None
    language: str
    duration_seconds: float


@dataclass(frozen=True)
class RuntimeConfig:
    repo_root: Path
    output_dir: Path
    transcripts_dir: Path
    ytstt: Path
    codex: Path
    model: str | None
    reasoning_effort: str
    review_passes: int
    project_name: str | None
    verbose: bool
    cookies_from_browser: str | None = None
    cookies: Path | None = None
    creative_direction: Path | None = None

    @property
    def creative_direction_path(self) -> Path:
        return (self.creative_direction or self.output_dir / "Globals/creative-direction.md").expanduser().resolve()
