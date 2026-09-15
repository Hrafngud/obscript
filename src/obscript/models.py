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
