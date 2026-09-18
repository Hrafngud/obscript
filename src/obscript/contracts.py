from __future__ import annotations

import re

from .models import CommandSpec

PIPELINES = {"remix", "split"}
TIME_CONTROLLERS = {"compress", "extend"}
FORMATS = {"topics", "essay"}
ALL_MODIFIERS = PIPELINES | TIME_CONTROLLERS | FORMATS


class ContractError(ValueError):
    pass


def parse_duration(value: str) -> int:
    raw = value.strip().lower()
    if re.fullmatch(r"\d+", raw):
        seconds = int(raw)
    elif re.fullmatch(r"\d+(?:\.\d+)?[smh]", raw):
        amount = float(raw[:-1])
        factor = {"s": 1, "m": 60, "h": 3600}[raw[-1]]
        seconds = round(amount * factor)
    elif re.fullmatch(r"(?:\d+:)?\d{1,2}:\d{2}", raw):
        parts = [int(part) for part in raw.split(":")]
        if len(parts) == 2:
            minutes, secs = parts
            hours = 0
        else:
            hours, minutes, secs = parts
        if minutes > 59 or secs > 59:
            raise ContractError(f"invalid duration: {value}")
        seconds = hours * 3600 + minutes * 60 + secs
    else:
        raise ContractError(
            f"invalid duration {value!r}; use seconds, 8m, 1.5h, MM:SS, or HH:MM:SS"
        )
    if seconds < 1:
        raise ContractError("duration must be greater than zero")
    return seconds


def split_sources(value: str) -> tuple[str, ...]:
    sources = tuple(part.strip() for part in value.split(",") if part.strip())
    if not sources:
        raise ContractError("a source is required")
    return sources


def parse_command_tokens(
    tokens: list[str],
    *,
    target_duration: str | None = None,
    split_count: int | None = None,
    render: bool = False,
    storybook: bool = False,
) -> CommandSpec:
    if not tokens:
        raise ContractError("a source is required")

    remaining = list(tokens)
    pipeline = remaining.pop(0) if remaining and remaining[0] in PIPELINES else "single"
    time_controller = (
        remaining.pop(0) if remaining and remaining[0] in TIME_CONTROLLERS else "normal"
    )
    format_name = remaining.pop(0) if remaining and remaining[0] in FORMATS else "source"

    misplaced = [token for token in remaining if token in ALL_MODIFIERS]
    if misplaced:
        raise ContractError(
            "modifiers must be ordered as pipeline → time-controller → format → source"
        )
    if len(remaining) != 1:
        raise ContractError(
            "provide one source argument; for remix, join sources with commas"
        )

    sources = split_sources(remaining[0])
    if pipeline == "remix" and len(sources) < 2:
        # A single playlist URL may expand into multiple sources after transcription.
        if "list=" not in sources[0]:
            raise ContractError("remix requires two or more comma-separated sources")
    elif pipeline != "remix" and len(sources) != 1:
        raise ContractError(f"{pipeline} accepts exactly one source")

    if split_count is not None:
        if pipeline != "split":
            raise ContractError("--into is only valid with split")
        if split_count < 2:
            raise ContractError("--into must be at least 2")

    target_seconds = parse_duration(target_duration) if target_duration else None
    if target_seconds is not None and time_controller == "normal" and pipeline != "split":
        raise ContractError(
            "--target-duration requires compress, extend, or split"
        )

    return CommandSpec(
        pipeline=pipeline,
        time_controller=time_controller,
        format=format_name,
        sources=sources,
        target_duration_seconds=target_seconds,
        split_count=split_count,
        render=render,
        storybook=storybook,
    )


def choose_target_duration(
    knowledge: dict,
    controller: str,
    explicit_seconds: int | None,
) -> int:
    if explicit_seconds:
        return explicit_seconds
    base = int(knowledge.get("recommended_duration_seconds") or 0)
    if base < 1:
        durations = [float(item.get("duration_seconds") or 0) for item in knowledge.get("sources", [])]
        base = round(max(durations, default=600))
    if controller == "compress":
        return max(60, round(base * 0.6))
    if controller == "extend":
        return max(60, round(base * 1.5))
    return max(1, base)


def script_duration_bounds(target_seconds: int) -> tuple[int, int]:
    """Inclusive integer-second bounds for the script review's ±30% tolerance."""
    if target_seconds < 1:
        raise ContractError("duration must be greater than zero")
    return (target_seconds * 70 + 99) // 100, target_seconds * 130 // 100
