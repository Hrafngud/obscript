from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


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
    storybook_scene_count: int | None = None
    project_id: str | None = None
    post_production: bool = False
    rerender_scene_id: str | None = None


@dataclass(frozen=True)
class SourceAsset:
    original: str
    title: str
    transcript_txt: Path
    transcript_srt: Path | None
    transcript_json: Path | None
    language: str
    duration_seconds: float
    media_source: str | None = None


@dataclass(frozen=True)
class VisualReferenceConfig:
    enabled: bool = True
    clip_count: int = 3
    clip_seconds: float = 15
    frames_per_clip: int = 6
    probe_count: int = 6
    probe_seconds: float = 4
    max_height: int = 480
    timeout_seconds: float = 180
    yt_dlp: Path = Path("yt-dlp")
    ffmpeg: Path = Path("ffmpeg")
    ffprobe: Path = Path("ffprobe")


@dataclass(frozen=True)
class PostProductionTarget:
    mode: Literal["scenes", "transition"]
    scene_ids: tuple[str, ...]


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
    cookies_from_browser: str | None = "firefox"
    cookies: Path | None = None
    creative_direction: Path | None = None
    harness: str = "codex"
    opencode: Path | None = None
    render_batch_size: int = 20
    post_production_batch_size: int = 20
    post_production_instruction: str | None = None
    post_production_target: PostProductionTarget | None = None
    visual_references: VisualReferenceConfig = field(default_factory=VisualReferenceConfig)

    @property
    def agent_executable(self) -> Path:
        return (self.opencode or Path("opencode")) if self.harness == "opencode" else self.codex

    @property
    def agent_name(self) -> str:
        return "OpenCode CLI" if self.harness == "opencode" else "Codex CLI"

    @property
    def creative_direction_path(self) -> Path:
        return (self.creative_direction or self.output_dir / "Globals/creative-direction.md").expanduser().resolve()
