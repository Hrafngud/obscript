from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from . import __version__
from .codex_agent import CodexError
from .contracts import ContractError, parse_command_tokens
from .models import RuntimeConfig
from .pipeline import Pipeline
from .production import ProductionError
from .transcribe import TranscriptionError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obscript",
        description="Generate original PT-BR scripts, visual pre-production, and optional silent HyperFrames animations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""ordered grammar:
  obscript [remix|split] [compress|extend] [topics|essay] <source>

examples:
  obscript VIDEO
  obscript compress essay VIDEO
  obscript remix extend topics VIDEO_A,VIDEO_B
  obscript split compress essay VIDEO --target-duration 8m
  obscript split topics VIDEO --into 4
  obscript extend essay VIDEO --render

For remix, comma-separate sources inside one shell argument. PT-BR normalization
is mandatory and has no translate modifier.
""",
    )
    parser.add_argument(
        "command",
        nargs="+",
        metavar="COMMAND",
        help="ordered modifiers followed by the required source argument",
    )
    parser.add_argument(
        "--target-duration",
        metavar="DURATION",
        help="target such as 480, 8m, 1.5h, or 08:00",
    )
    parser.add_argument("--into", type=int, metavar="COUNT", help="desired split count")
    parser.add_argument("--project", help="Obsidian project folder name")
    parser.add_argument(
        "--output-dir",
        "--vault",
        dest="output_dir",
        type=Path,
        default=Path("/home/zalmo/documents/obsidian/Videos/Videos"),
        help=(
            "rescript project root "
            "(default: /home/zalmo/documents/obsidian/Videos/Videos)"
        ),
    )
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        default=Path("/home/zalmo/transcripts"),
        help="ytstt output root (default: /home/zalmo/transcripts)",
    )
    parser.add_argument(
        "--ytstt",
        type=Path,
        default=Path("/home/zalmo/.local/bin/ytstt"),
        help="ytstt executable",
    )
    parser.add_argument(
        "--codex",
        type=Path,
        default=None,
        help="Codex CLI executable (default: resolve from PATH)",
    )
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument(
        "--cookies-from-browser",
        default=os.environ.get("OBSCRIPT_COOKIES_FROM_BROWSER"),
        metavar="BROWSER[:PROFILE]",
        help="use a logged-in browser for YouTube; auto retries with a detected browser when blocked",
    )
    auth.add_argument(
        "--cookies", type=Path, metavar="FILE",
        help="use an exported Netscape cookies file instead of browser cookies",
    )
    parser.add_argument("--model", help="Codex model override; default uses Codex config")
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high", "xhigh"],
        default="medium",
        help="Codex reasoning effort per stage (default: medium)",
    )
    parser.add_argument(
        "--review-passes",
        type=int,
        default=2,
        help="maximum review passes including the first (default: 2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the execution stages without transcribing or invoking Codex",
    )
    parser.add_argument(
        "--render", action="store_true",
        help="render silent animations through the installed HyperFrames skill",
    )
    parser.add_argument("--verbose", action="store_true", help="stream Codex CLI output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _resolve_codex(requested: Path | None) -> Path:
    if requested:
        return requested.expanduser().resolve()
    found = shutil.which("codex")
    if not found:
        raise ContractError("Codex CLI was not found in PATH; pass --codex")
    return Path(found).resolve()


def _print_dry_run(spec) -> None:
    stages = ["ytstt/source import", "analyze-source"]
    if spec.pipeline != "single":
        stages.append(spec.pipeline)
    if spec.time_controller != "normal":
        stages.append(spec.time_controller)
    if spec.format != "source":
        stages.append(spec.format)
    stages.extend(["plan-script", "write-script", "review-script", "creative-direction", "storybook", "validate-storybook"])
    if spec.render:
        stages.extend(["produce-video", "package-production"])
    print("pipeline: " + " → ".join(stages))
    print(f"sources: {len(spec.sources)}")
    print(f"target_duration_seconds: {spec.target_duration_seconds or 'automatic'}")
    if spec.split_count:
        print(f"split_count: {spec.split_count}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        spec = parse_command_tokens(
            args.command,
            target_duration=args.target_duration,
            split_count=args.into,
            render=args.render,
        )
        if args.review_passes < 1:
            raise ContractError("--review-passes must be at least 1")
        if args.dry_run:
            _print_dry_run(spec)
            return 0

        repo_root = Path(__file__).resolve().parents[2]
        codex = _resolve_codex(args.codex)
        if not args.ytstt.expanduser().exists():
            raise ContractError(f"ytstt executable does not exist: {args.ytstt}")
        args.output_dir.expanduser().mkdir(parents=True, exist_ok=True)
        args.transcripts_dir.expanduser().mkdir(parents=True, exist_ok=True)
        config = RuntimeConfig(
            repo_root=repo_root,
            output_dir=args.output_dir.expanduser().resolve(),
            transcripts_dir=args.transcripts_dir.expanduser().resolve(),
            ytstt=args.ytstt.expanduser().resolve(),
            codex=codex,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            review_passes=args.review_passes,
            project_name=args.project,
            verbose=args.verbose,
            cookies_from_browser=args.cookies_from_browser if not args.cookies else None,
            cookies=args.cookies.expanduser().resolve() if args.cookies else None,
        )
        result = Pipeline(config).run(spec)
    except (ContractError, TranscriptionError, CodexError, ProductionError, OSError) as exc:
        print(f"obscript: {exc}", file=sys.stderr)
        return 1

    print(f"[obscript] projeto: {result.project_root}")
    for output in result.outputs:
        print(f"[obscript] artefato: {output}")
    if not result.passed_review:
        print(
            "[obscript] aviso: o roteiro foi salvo, mas ainda requer revisão; consulte review.yaml",
            file=sys.stderr,
        )
        return 2
    print("[obscript] revisão aprovada")
    return 0
