# obscript

`obscript` turns video sources or existing transcripts into original Brazilian Portuguese video scripts. Codex is the agent backend; `ytstt` supplies local speech-to-text. Every model stage reads and returns a structured intermediate representation instead of rewriting a transcript directly.

```text
source → analyze-source → pipeline → time → format
       → plan-script → write-script → review-script
```

## Install

The local defaults match this workstation:

- Codex CLI from `PATH`
- `ytstt`: `/home/zalmo/.local/bin/ytstt`
- transcripts: `/home/zalmo/transcripts`
- rescript output root: `/home/zalmo/documents/obsidian/Videos/Videos`

Install the executable and symlink all versioned skills into the Codex skill directory:

```bash
./scripts/install.sh
```

The installer refuses to replace ordinary files or unrelated symlinks.

## CLI

The positional grammar is fixed:

```text
obscript [remix|split] [compress|extend] [topics|essay] <source>
```

Examples:

```bash
obscript VIDEO
obscript compress essay VIDEO
obscript extend topics VIDEO --target-duration 20m
obscript remix compress essay 'VIDEO_A,VIDEO_B,VIDEO_C' --target-duration 12m
obscript split topics VIDEO --into 4
obscript split compress essay VIDEO --target-duration 8m
```

`remix` takes two or more comma-separated sources. A playlist URL is accepted as the single remix argument when `ytstt` expands it into at least two videos. A playlist without `remix` produces one independent script per item. `split` takes one non-playlist video. Translation is always conceptual PT-BR normalization during `analyze-source`; there is no `translate` modifier.

A source may be a video URL, playlist URL, local media file, transcript directory, or `.txt`, `.srt`, `.vtt`, or `ytstt` `.json` transcript.

Without a target, `compress` aims at 60% of the model's recommended/source duration and `extend` at 150%. Without a time controller, the source or model-recommended duration is retained. Use `--dry-run` to validate a command without transcription or Codex calls.

Each stage uses the model configured in Codex and `medium` reasoning effort by default. Override these with `--model` and `--reasoning-effort` when needed.

## Artifacts

Each run creates a collision-safe project under `/home/zalmo/documents/obsidian/Videos/Videos/<project>/`:

```text
sources/source-01-.../
  transcript.txt
  transcript.srt
  transcript.json
  source.json
  analysis.yaml
knowledge.yaml
plan.md
script.md
review.yaml
run.yaml
.obscript/                 # exact JSON stage state and prompts
```

Split runs place `split-plan.yaml` at the project root and the five primary artifacts under `video-01/`, `video-02/`, and so on. Independent playlist runs use the same child layout plus `playlist-plan.yaml`. If the last review still requests revision, artifacts remain available and the CLI exits with status 2.

## Skills

The versioned skill set is:

```text
analyze-source      remix       compress      topics      plan-script
translate-context   split       extend        essay       write-script
review-script
```

They can be invoked directly in Codex (for example, `$review-script`) or are loaded explicitly by the CLI for their respective stage. `translate-context` is an internal/import repair skill because ordinary analysis already emits canonical PT-BR knowledge.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

Structured-output schemas live in `schemas/`; the CLI invokes `codex exec --output-schema` in a read-only sandbox and performs all artifact writes itself.
