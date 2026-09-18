# obscript

`obscript` creates formatted projects for scripts you write from scratch, or turns video sources and existing transcripts into original Brazilian Portuguese video scripts, visual pre-production, and optionally rendered silent animations. Codex is the default agent harness; pass `--opencode` to use OpenCode throughout the pipeline. `ytstt` supplies local speech-to-text. Every model stage reads and returns a structured intermediate representation instead of rewriting a transcript directly.

```text
source → analyze-source → pipeline → time → format
       → plan-script → write-script → review-script
                                      ↓ pass
                                      ↓ --storybook or --render
       → storybook → validate-storybook
                                      ↓ --render
       → produce-video → package-production
                                      ↓ PROJECT_ID --post-production
       → validate-production → post-production → verify-post-production
```

## Install

The local defaults match this workstation:

- Codex CLI from `PATH`, or OpenCode CLI from `PATH` with `--opencode`
- `ytstt`: `/home/zalmo/.local/bin/ytstt`
- transcripts: `/home/zalmo/transcripts`
- rescript output root: `/home/zalmo/documents/obsidian/Videos/Videos`
- shared visual standards: `OUTPUT_DIR/Globals/creative-direction.md`

Install the executable and symlink all versioned skills into the Codex skill directory:

```bash
./scripts/install.sh
```

The installer refuses to replace ordinary files or unrelated symlinks.

OpenCode uses its existing provider authentication and model configuration. The adapter adds the repository's skills and the existing `${CODEX_HOME:-~/.codex}/skills` directory to OpenCode's skill discovery for each run, including HyperFrames skills installed there. No separate skill installation or global configuration changes are needed to switch harnesses. HyperFrames and its dependencies are still required for rendering.

## CLI

Start an original script without a video or transcript:

```bash
obscript new
obscript new "Minha ideia original" --target-duration 8m --format essay
obscript new "Título do vídeo" --project "Nome da pasta" --vault /path/to/vault
obscript new --dry-run
```

`new` creates a collision-safe project folder containing `script.md`, `project.json`, and `run.yaml`. Open `script.md` in Obsidian or your editor and replace the thesis and narration placeholders. The template uses the existing PT-BR Markdown front matter and includes hook, introduction, development, and conclusion sections. Its defaults are title `Novo roteiro`, format `topics`, and a 10-minute target; `--project` supplies the title when no positional title is given. `--format` accepts `source`, `topics`, or `essay` for this command.

Original projects receive a permanent UUID, timestamps, shared creative-direction path, and `origin: original` / `status: draft` metadata. Their source list is empty. Creation needs neither ytstt nor Codex, does not create a transcripts directory, and does not require the shared creative-direction file to exist. These are manual drafts: `new` does not generate or review narration, and ID-based storybook/render processing is not supported for these projects. `--storybook`, `--render`, and `--into` are rejected with `new`. A dry run creates no files.

For processing existing sources, the positional grammar is:

```text
obscript [remix|split] [compress|extend] [topics|essay] <source>
```

Examples:

```bash
obscript VIDEO
obscript compress essay VIDEO
obscript extend topics VIDEO --target-duration 20m
obscript extend essay VIDEO --storybook
obscript extend essay VIDEO --render
obscript extend essay VIDEO --render --dry-run
obscript remix compress essay 'VIDEO_A,VIDEO_B,VIDEO_C' --target-duration 12m
obscript split topics VIDEO --into 4
obscript split compress essay VIDEO --target-duration 8m
obscript PROJECT_ID --storybook
obscript PROJECT_ID --render
obscript VIDEO --render --opencode
obscript PROJECT_ID --render --opencode
obscript PROJECT_ID --post-production
obscript PROJECT_ID --post-production --dry-run
```

`remix` takes two or more comma-separated sources. A playlist URL is accepted as the single remix argument when `ytstt` expands it into at least two videos. A playlist without `remix` produces one independent script per item. `split` takes one non-playlist video. Translation is always conceptual PT-BR normalization during `analyze-source`; there is no `translate` modifier.

A source may be a video URL, playlist URL, local media file, transcript directory, or `.txt`, `.srt`, `.vtt`, or `ytstt` `.json` transcript.

Install cookie support for the workstation's existing `ytstt` once:

```bash
python3 scripts/install-ytstt-auth.py --apply
```

The installer backs up `ytstt.py` before patching it and installs the versioned authentication adapter beside it. Omit `--apply` to review the diff; use `--ytstt-home PATH` for another installation. Reapply after a `ytstt` update if needed.

Obscript always passes `--cookies-from-browser firefox` to ytstt by default. With the adapter installed, Firefox cookies are loaded before the first request, for both URL inspection and audio downloads, including individual playlist items. Sign in to YouTube in Firefox. Reapply the installer above to update an already installed adapter. To choose a browser or profile explicitly:

```bash
obscript 'https://www.youtube.com/watch?v=C3-FIM2xTIw' --render
obscript VIDEO --cookies-from-browser firefox
obscript VIDEO --cookies-from-browser 'chrome:Default'
obscript VIDEO --cookies /path/to/cookies.txt
```

Set `OBSCRIPT_COOKIES_FROM_BROWSER` in your shell to override the default browser. The legacy `auto` selector also uses Firefox from the first request. Use `--cookies-from-browser none` to explicitly disable cookies, or `--cookies FILE` to use an exported file instead. Exported files must use Netscape cookie format. If YouTube rejects the cookies, refresh the browser login and retry; cookies cannot guarantee access against every YouTube restriction.

Without a target, `compress` aims at 60% of the model's recommended/source duration and `extend` at 150%. Without a time controller, the source or model-recommended duration is retained. Use `--dry-run` to validate a command without transcription or agent calls. `--dry-run --render` includes the production stages in the plan and makes no HyperFrames calls or media files.

Without a phase flag, a run stops after script review. `--storybook` continues through visual planning and validation, producing an Obsidian-readable `storybook.md` and the structured `storybook.yaml`, without rendering. `--render` runs any missing script and storybook phases, then creates silent animations through the installed `$hyperframes` skill. These flags are mutually exclusive.

Each new project has a permanent UUID in `project.json`, printed before processing starts. Resume with `obscript PROJECT_ID --storybook` or `obscript PROJECT_ID --render`; use the same `--output-dir` or `--vault` as the original run. The project keeps its sources, modifiers, target duration, split settings, and shared direction path. Completed imports, analyses, remix/split results, approved scripts, validated storybooks, and unchanged completed renders are reused. Failed runs keep their checkpoints and ID, including projects that only reached transcript import. Split and independent playlist projects resume each child video in the same project. Running the original source again creates a separate project; ID lookup applies to projects created with this metadata.

For manual visual edits, change `storybook.yaml`, the authoritative production plan. Resuming revalidates it without regenerating it, including its exact narration and timing constraints. Invalid edits remain available for correction and block rendering. `storybook.md` is the readable view; edits to that Markdown are preserved as notes but do not change the structured render plan. Readable storybooks and script timestamp cues are refreshed from YAML changes when their Markdown has not been manually edited. Reviewed structured script inputs cannot be changed while reusing their old approval.

Planning and production both read the same shared `Globals/creative-direction.md`; no per-video creative-direction file or visual identity-generation stage is created. Use `--creative-direction FILE` to select another shared file, including when using a different `--output-dir` or `--vault`. The shared file must exist and contain standards or a field template for storybook or render requests; script-only runs and dry runs do not read it. Filled fields are binding; blank fields and suggestions remain unspecified, with execution details resolved in each scene plan. Obscript never edits the shared file. After storybook validation, `script.md` includes section and scene timestamp cues for a human reader. Rendering does not change the approved narration and uses local HyperFrames projects with Node.js 22+, FFmpeg/ffprobe, and the installed HyperFrames skills.

The workflow is script → timed animations → human voiceover and audio editing. Obscript generates no audio, TTS, music, sound effects, or automatic subtitles. Storybook timestamps define the animation timeline and the human recording cues; production never retimes scenes against generated speech.

Each stage uses the selected harness's configured default model. Codex uses `medium` reasoning effort by default; override it with `--reasoning-effort`. OpenCode uses its own configured reasoning settings; the Codex reasoning option does not override them. `--model` overrides the model in either harness (OpenCode expects `provider/model`).

`--opencode` applies to every agent stage: analysis, remix/split, duration and format transformations, planning, writing, review, storybook, rendering, and post-production. It works with sources and project IDs, for example `obscript PROJECT_ID --post-production --opencode`. Completed checkpoints and verified media are shared between harnesses; pass `--opencode` on any invocation that should use OpenCode, or omit it to use Codex. `--opencode-bin FILE` overrides OpenCode's executable and requires `--opencode`; `--codex FILE` and `--opencode` are mutually exclusive. Dry runs require neither harness to be installed.

## Artifacts

Each new run creates a collision-safe project under `/home/zalmo/documents/obsidian/Videos/Videos/<project>/`; ID-based runs reuse that directory:

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
storybook.md              # readable scene plan, with --storybook or --render
storybook.yaml            # editable production plan, with --storybook or --render
production/               # only with --render
  hyperframes/            # shared editable composition project
  scenes/scene-001/
    manifest.json
    ...silent rendered scene media...
production.yaml           # only after a render attempt
video.mp4                 # silent animations, only after verified assembly
post-production/          # optional polish pass; source production stays intact
  hyperframes/            # editable copy with polished effects and transitions
  report.md               # affected scenes, treatments, and visual checks
post-production.yaml      # polish status, source hash, duration, output paths
video-polished.mp4        # verified silent post-production result
run.yaml
project.json              # permanent ID, original command, phase and status
.obscript/                 # exact JSON stage state and prompts
```

A normal run or remix is one production unit. Split runs place `split-plan.yaml` at the project root; each `video-01/`, `video-02/`, and so on owns its knowledge, plan, script, review, visual artifacts, production files, and `.obscript/` state. Independent playlists use the same child layout plus `playlist-plan.yaml`.

If the last script review still requests revision, `script.md` and `review.yaml` remain available and the CLI exits with status 2. No visual stages or rendering run for that unit. Application validation rejects invented, missing, duplicated, or reordered voiceover; unknown or uncovered sections; nonsequential scenes; and gaps, overlaps, or incorrect timeline endpoints. Invalid storybooks are regenerated up to three times, with attempts and validation errors retained in `.obscript/`; continued failure exits with status 1 before production and leaves `storybook.md` marked `status: invalid`, including the last draft and its validation error. Successful plans use `status: validated`.

The approved structured script in `.obscript/approved-script.json` is the sole spoken source. Scenes partition its narration into exact contiguous excerpts, each bound to one section. The shared creative-direction Markdown supplies visual standards to all videos. `storybook.md` links to that source, and `.obscript/creative-direction-source.json` records its absolute path and content hash without copying its standards. `storybook.md` displays an English timeline and a concise Scene / Layout paragraph for each scene: concrete elements, asset references, positions, backgrounds, timed animation, camera moves, and transitions. These production directions describe what appears rather than re-explaining narration. Narration and on-screen labels keep their original language. `storybook.yaml` retains the complete structured scene fields and exact narration references. `storybook.yaml` remains the structured production plan and is revalidated before rendering. Scene durations primarily fall between 3 and 12 seconds and become the animation's allocated intervals. `voiceover.text` remains the exact human narration reference, not a request to generate speech. The same boundaries appear in `script.md` as `HH:MM:SS.mmm` cues at section and scene level. On-screen text supplements narration. Text density is a layout and readability choice, with no fixed word-count limit and no word-count validation gate.

Rendering uses one run of the selected harness per video through `ProductionAgent`, which invokes `$produce-video` and delegates animation execution to the installed `$hyperframes` skill. The handoff contains the verbatim shared creative-direction Markdown, its source path, and the complete storybook, immutable narration references, planned timestamps, scene output destinations, final video destination, and settled `general-video` intent (`flow: automation`, `storyboard: no`, no narration). The same agent produces every scene and the final assembly, reusing loaded skills and creative context without launching additional harness runs. The producer initializes one editable project at `production/hyperframes/` and writes its `BRIEF.md` after initialization. Defaults are 1920×1080 at 30 fps; the explicit `--render` request supplies render authorization after required quality checks.

Scene planning and rendering prefer the local visual asset library at `/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets` for general illustrations, technical icons, emojis, backgrounds, and textures, including animated interactions. Agents inspect existing files before selecting them and use suitable library assets before inventing SVGs, generating images, or searching external stock. Production copies selected assets into its editable project, carries the preference and asset mapping into `BRIEF.md`, and may recolor monochrome fills/strokes or animate icons and internal parts to match the shared direction and scene timing. Background collections such as `backgrounds1` are evaluated by intrinsic dimensions, aspect ratio, and visible content: sufficiently resolved images can cover the frame, while tiny raster textures are repeated at a suitable scale or confined to sides and other regions. Backgrounds and patterns may be rotated, tilted, cropped, or layered, with enough coverage to avoid gaps and preserve foreground readability. The shared library remains unchanged; explicit assets and meaningful brand or emoji colors are preserved.

The agent writes a durable manifest and silent video for each scene. After the run, the application verifies each scene with ffprobe: it must contain video, contain no audio track, and match its planned duration within one frame. Final assembly places scenes at the exact storybook timestamps and applies visual transitions inside those allocated intervals, preserving the planned total duration. Only a successful run with verified scenes and a verified complete assembly publishes the silent `video.mp4`. `production.yaml` records `backend: hyperframes`, `audio: false`, and `status: complete` or `status: failed`; executor failures still allow verification of completed scenes, preserve partial output, and leave `final_video` empty. The CLI exits with status 1 for production failures.

For example, a human sees this cue in `script.md` and records the exact passage for that animation interval:

```markdown
### scene-001 · 00:00:00.000 → 00:00:03.000

Você observa o padrão.
```

Upstream changes archive stale derivatives under `.obscript/invalidated/`, removing them from current output. A script revision invalidates storybook, production, and the recorded direction reference (archiving legacy per-video direction files when present); a direction change invalidates storybook and production; a storybook change invalidates production. Changes to shared standards require `obscript PROJECT_ID --storybook` to rebuild affected scene plans before rendering; a content-hash check blocks rendering a storybook planned against different standards. Production checks that its upstream inputs remain unchanged and validates the returned scene artifacts before publication. An interrupted render with unchanged inputs retains its editable HyperFrames project and marks verified completed scene media for reuse; changed inputs archive previous production. A completed render is skipped only when its inputs and final video hash still match. There is no automatic filesystem watcher.

`obscript PROJECT_ID --post-production` runs a separate visual finishing pass on a completed render. It requires an existing project ID and is mutually exclusive with `--storybook` and `--render`; `new` does not support it. The pass does not transcribe, rewrite, review, replan, or automatically perform the initial render. Every video in a split or playlist project must have a completed render, and all are checked before polishing begins. Stale approved inputs, changed shared standards or storybooks, missing editable source, changed original video, invalid scene media, or missing ffprobe block the pass. Rebuild changed standards with `--storybook`, then run `--render` before retrying.

The dedicated `$post-production` agent inspects the existing video and edits a copy of `production/hyperframes/` under `post-production/hyperframes/`. It concentrates on flat or poorly polished moments: compatible vignettes and overlay textures, clearer element-focused effects, and varied transitions motivated by adjacent scenes. It may refine visual treatments and transitions in the copy while preserving narration, meaning, shared visual identity, scene order, and every planned boundary. The explicit flag authorizes local silent rendering after HyperFrames quality checks. The agent retains visual verification artifacts and a scene-by-scene `post-production/report.md`.

The application preserves `video.mp4` and the source production project, checks source input hashes after execution, and verifies that the polished assembly contains video, contains no audio, and matches the total duration within one frame. Only a successful pass with a nonempty report publishes `video-polished.mp4`; `post-production.yaml` records completion or failure. Failed runs preserve partial editable work for retry with unchanged source inputs. A verified completed pass is reused while source inputs, polished video, and report hashes match. Source changes archive stale polish output under `.obscript/invalidated/`. Dry runs print only the post-production stages and create no files. One agent run executes each video's complete pass.

The request and prompt remain in `.obscript/post-production.request.json` and `.obscript/post-production.prompt.txt`; the response and executor log remain in `post-production/` for inspection.

## Skills

The versioned skill set is:

```text
analyze-source      remix       compress      topics      plan-script
translate-context   split       extend        essay       write-script
review-script       creative-direction       storybook       produce-video
post-production
obscript-parse-script
```

`creative-direction` is a read-only reference skill for the shared standards, not a generation stage.

`obscript-parse-script` interprets inline narration annotations during Storybook planning: `*element*` zooms in and out, `**element**` wiggles, inline backticks pulse, `~~element~~` adds a red overlay and ❌ above the element, and `%%element%%` adds a green overlay and ✅ above it. Cues use approximate word positions within each scene, preserve the approved narration, and are recorded in the existing animation and render brief fields. It can also be invoked directly to update a storybook; it does not render video or add a separate CLI stage.

They can be invoked directly in Codex (for example, `$review-script`) or are loaded explicitly by the CLI for their respective stage. `translate-context` is an internal/import repair skill because ordinary analysis already emits canonical PT-BR knowledge.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

Structured-output schemas live in `schemas/`. Reasoning stages use `CodexAgent` with `codex exec --output-schema` in a read-only sandbox; the application writes their returned artifacts. Media execution uses a separate `ProductionAgent` with a single workspace-write run rooted at the production directory, no structured-output schema, and network access for HyperFrames dependencies and specified visual assets. This follows the [official Codex sandbox configuration](https://learn.chatgpt.com/docs/security). The complete production request and prompt remain in `.obscript/produce-video.request.json` and `.obscript/produce-video.prompt.txt`; the response and executor log remain in `production/` for inspection.

With OpenCode, both paths use native [`opencode run --format json`](https://opencode.ai/docs/cli/#run), sending prompts through stdin and retaining the configured model and agent. Structured stages receive the same schemas in the prompt; the adapter extracts the final assistant message, validates it using the shared validator for obscript's schema keywords, and saves only valid structured checkpoints. Raw events and responses remain in `.obscript/` for inspection. Temporary [OpenCode configuration](https://opencode.ai/docs/config/) adds skill paths and stage permissions without editing user config files. Reasoning permits only reading and searching inputs. Production permits shell execution and limits direct file-edit tools to the requested output directory, blocks nested agents and interactive questions, and retains `executor.log` and `agent-response.txt`. OpenCode's tool permissions do not provide Codex's OS sandbox; shell execution follows the immutable-input prompt and application hash checks used to validate production artifacts.

The tests use a simulated HyperFrames executor, verify exact script-to-scene coverage and human timestamp cues, reject scene and final-duration drift, and exercise real local silent video assembly when FFmpeg tools are available. No live model-driven HyperFrames render runs in the test suite.
