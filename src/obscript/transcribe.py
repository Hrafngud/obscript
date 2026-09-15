from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from .models import SourceAsset
from .storage import unique_directory


class TranscriptionError(RuntimeError):
    pass


def _duration_from_srt(path: Path) -> float:
    matches = re.findall(r"-->\s*(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})", path.read_text(encoding="utf-8", errors="replace"))
    if not matches:
        return 0.0
    hours, minutes, seconds, millis = map(int, matches[-1])
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def _asset_from_directory(directory: Path, original: str) -> SourceAsset:
    txt = directory / "transcript.txt"
    if not txt.exists():
        candidates = sorted(directory.glob("*.txt"))
        if not candidates:
            raise TranscriptionError(f"no transcript.txt found in {directory}")
        txt = candidates[0]
    srt = directory / "transcript.srt"
    json_path = directory / "transcript.json"
    metadata: dict = {}
    if json_path.exists():
        try:
            metadata = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            metadata = {}
    duration = float(metadata.get("duration") or 0)
    if not duration and srt.exists():
        duration = _duration_from_srt(srt)
    if not duration:
        word_count = len(txt.read_text(encoding="utf-8", errors="replace").split())
        duration = max(1.0, word_count / 2.5)
    return SourceAsset(
        original=original,
        title=str(metadata.get("title") or directory.name or txt.stem),
        transcript_txt=txt.resolve(),
        transcript_srt=srt.resolve() if srt.exists() else None,
        transcript_json=json_path.resolve() if json_path.exists() else None,
        language=str(metadata.get("language") or "unknown"),
        duration_seconds=duration,
    )


def _subtitle_to_text(content: str) -> str:
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", content.replace("\r\n", "\n")):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        lines = [
            line
            for line in lines
            if not line.isdigit()
            and "-->" not in line
            and line.upper() != "WEBVTT"
            and not line.upper().startswith("NOTE ")
        ]
        text = " ".join(lines).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs).strip() + "\n"


def _normalize_transcript_file(local: Path, source: str, transcripts_dir: Path) -> SourceAsset:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    directory = unique_directory(transcripts_dir, f"obscript-import-{stamp}")
    suffix = local.suffix.lower()
    if suffix == ".txt":
        shutil.copy2(local, directory / "transcript.txt")
    elif suffix in {".srt", ".vtt"}:
        shutil.copy2(local, directory / f"transcript{suffix}")
        content = local.read_text(encoding="utf-8", errors="replace")
        (directory / "transcript.txt").write_text(
            _subtitle_to_text(content), encoding="utf-8"
        )
    elif suffix == ".json":
        try:
            payload = json.loads(local.read_text(encoding="utf-8"))
            segments = payload["segments"]
            text = "\n\n".join(
                str(segment.get("text") or "").strip()
                for segment in segments
                if str(segment.get("text") or "").strip()
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise TranscriptionError(
                f"JSON transcript must contain a segments array: {local}"
            ) from exc
        shutil.copy2(local, directory / "transcript.json")
        (directory / "transcript.txt").write_text(text.strip() + "\n", encoding="utf-8")
    asset = _asset_from_directory(directory, source)
    if asset.title == directory.name:
        asset = replace(asset, title=local.stem)
    return asset


def ingest_source(source: str, *, ytstt: Path, transcripts_dir: Path) -> list[SourceAsset]:
    local = Path(source).expanduser()
    if local.is_dir():
        return [_asset_from_directory(local.resolve(), source)]
    if local.is_file() and local.suffix.lower() in {".txt", ".srt", ".vtt", ".json"}:
        return [_normalize_transcript_file(local.resolve(), source, transcripts_dir)]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    batch = unique_directory(transcripts_dir, f"obscript-{stamp}")
    command = [str(ytstt), source, "--output-dir", str(batch), "--format", "txt,srt,json"]
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise TranscriptionError(f"ytstt executable not found: {ytstt}") from exc
    except subprocess.CalledProcessError as exc:
        raise TranscriptionError(f"ytstt failed for {source!r} with exit code {exc.returncode}") from exc
    directories = sorted(path for path in batch.iterdir() if path.is_dir())
    if not directories:
        raise TranscriptionError(f"ytstt produced no transcript directories in {batch}")
    return [_asset_from_directory(path, source) for path in directories]
