"""A live run panel for the CLI, with plain output for logs."""
from __future__ import annotations

import os
import re
import shutil
import sys
import threading
import time
from contextvars import ContextVar
from typing import TextIO


_active: ContextVar[RunProgress | None] = ContextVar("obscript_progress", default=None)


def _phase(stage: str) -> str:
    for prefix, label in (
        ("transcribe", "Transcription"), ("import", "Importing sources"),
        ("analyze-visual", "Visual references"), ("visual-references", "Visual references"),
        ("analyze-source", "Source analysis"), ("review-storybook", "Storybook review"),
        ("recheck-storybook", "Storybook review"), ("repair-storybook", "Storybook repair"),
        ("validate-storybook", "Validating storybook"), ("storybook", "Storybook planning"),
        ("review-script", "Script review"), ("plan-script", "Script planning"),
        ("write-script", "Writing script"), ("produce-video", "Rendering video"),
        ("verify-render", "Verifying video"), ("post-production", "Post-production"),
        ("verify-post-production", "Verifying post-production"),
    ):
        if stage.startswith(prefix):
            return label
    return stage.replace("-", " ").capitalize()


def _clean(value: str) -> str:
    # Paths, titles, and external messages must not control the live terminal.
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", value)


def _elapsed(seconds: float) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def report(stage: str, detail: str = "") -> None:
    progress = _active.get()
    if progress is not None:
        progress.update(stage, detail)
    else:
        print(f"[obscript] {_phase(stage)} · {detail or stage}", file=sys.stderr, flush=True)


def announce(message: str) -> None:
    """Keep durable messages readable without disrupting the live status line."""
    progress = _active.get()
    if progress is None:
        print(message, flush=True)
    else:
        progress.write(message)


def report_project(project: str) -> None:
    progress = _active.get()
    if progress is not None:
        progress.set_project(project)


class RunProgress:
    def __init__(self, *, verbose: bool = False, stream: TextIO | None = None,
                 agent: str | None = None, model: str | None = None,
                 effort: str | None = None, project: str | None = None) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.live = self.stream.isatty() and os.environ.get("TERM") != "dumb" and not verbose
        self.context = {label: _clean(value) for label, value in (
            ("Agent", agent), ("Model", model), ("Effort", effort), ("Project", project),
        ) if value is not None}
        self.stage = "starting"
        self.detail = ""
        self.started = self.phase_started = time.monotonic()
        self.outcome = "Completed"
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._frame = 0
        self._line_count = 0

    def __enter__(self) -> RunProgress:
        self._token = _active.set(self)
        if self.live:
            self._draw()
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
        else:
            for label, value in self.context.items():
                print(f"[obscript] {label}: {value}", file=self.stream, flush=True)
        return self

    def set_project(self, project: str) -> None:
        with self._lock:
            project = _clean(project)
            if self.context.get("Project") == project:
                return
            self.context["Project"] = project
            if self.live:
                self._draw()
            else:
                print(f"[obscript] Project: {project}", file=self.stream, flush=True)

    def update(self, stage: str, detail: str = "") -> None:
        with self._lock:
            stage, detail = _clean(stage), _clean(detail)
            if (stage, detail) == (self.stage, self.detail):
                return
            if _phase(stage) != _phase(self.stage):
                self.phase_started = time.monotonic()
            self.stage, self.detail = stage, detail
            if self.live:
                self._draw()
            else:
                print(f"[obscript] {_phase(stage)} · {detail or stage}", file=self.stream, flush=True)

    def write(self, message: str) -> None:
        with self._lock:
            if self.live:
                self._clear()
                self.stream.flush()
            print(message, flush=True)
            if self.live:
                self._draw()

    def _clear(self) -> None:
        for index in range(max(1, self._line_count)):
            self.stream.write("\r\033[2K")
            if index < self._line_count - 1:
                self.stream.write("\033[1A")
        self._line_count = 0

    def _draw(self, status: str | None = None) -> None:
        now = time.monotonic()
        spinner = "|/-\\"[self._frame % 4]
        self._frame += 1
        timing = f"{_elapsed(now - self.phase_started)} phase / {_elapsed(now - self.started)} total"
        label = f"{spinner} {_phase(self.stage)} · {self.detail or self.stage}"
        width = max(1, shutil.get_terminal_size(fallback=(80, 24)).columns - 1)
        available = width - len(timing) - 3
        if available >= 20:
            if len(label) > available:
                label = label[:available - 3] + "..."
            line = f"{label} | {timing}"
        else:
            line = f"{spinner} {_phase(self.stage)} | {_elapsed(now - self.started)}"
        lines = [f"{label}: {value}" for label, value in self.context.items()]
        lines.append(status if status is not None else line)
        self._clear()
        self.stream.write("\n".join(value[:width] for value in lines))
        self._line_count = len(lines)
        self.stream.flush()

    def _animate(self) -> None:
        while not self._stop.wait(0.12):
            with self._lock:
                self._draw()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join()
        _active.reset(self._token)
        outcome = "Interrupted" if exc_type is KeyboardInterrupt else "Failed" if exc_type else self.outcome
        status = f"[obscript] {outcome} · {_phase(self.stage)} · {_elapsed(time.monotonic() - self.started)}"
        if self.live:
            self._draw(status)
            print(file=self.stream, flush=True)
        else:
            print(status, file=self.stream, flush=True)
