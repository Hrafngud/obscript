# obscript

`obscript` creates formatted projects for scripts you write from scratch, or turns video sources and existing transcripts into original Brazilian Portuguese video scripts, visual pre-production, and optionally rendered silent animations. Codex is the default agent harness; pass `--opencode` to use OpenCode throughout the pipeline. `ytstt` supplies local speech-to-text. Every model stage reads and returns a structured intermediate representation instead of rewriting a transcript directly.

```text
source → analyze-source → pipeline → time → format
       → plan-script → write-script → review-script
                                      ↓ pass
                                      ↓ --storybook or --render
       → visual-references (source videos, cached, best effort)
       → storybook → validate-storybook → review-storybook
                                      ↓ targeted repair + recheck if needed
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
- visual reference sampling: `yt-dlp`, FFmpeg and FFprobe from `PATH`, plus an image-capable agent model

Install the executable and symlink all versioned skills into the Codex skill directory:

```bash
./scripts/install.sh
```

The installer refuses to replace ordinary files or unrelated symlinks.

OpenCode uses its existing provider authentication and model configuration. The adapter adds the repository's skills and the existing `${CODEX_HOME:-~/.codex}/skills` directory to OpenCode's skill discovery for each run, including HyperFrames skills installed there. No separate skill installation or global configuration changes are needed to switch harnesses. HyperFrames and its dependencies are still required for rendering.

## CLI

During a run, an interactive terminal shows a live panel with the agent (Codex or OpenCode), model, reasoning effort, project folder name, current phase, stage or batch, phase elapsed time, and total elapsed time. Agent settings stay visible as the phase changes. Inherited model settings are labeled `configured default`; OpenCode also uses this label for effort because it manages its own setting. Redirected output and `TERM=dumb` print the run details followed by plain progress lines without animation. Use `--verbose` to show transcription and agent output with plain progress lines. Otherwise, ytstt output is saved to `TRANSCRIPTS_DIR/obscript-*/ytstt.log`; transcription failures point to that log.

Successful `--storybook` runs end with a copyable `--render` command. Completed renders (including `--re-render`) suggest post-production commands for a full polish pass, custom direction, and a scene adjustment. Commands include the project ID, output directory, and selected agent settings so they can be run from another directory. Runs that fail or still need script review do not suggest advancing to the next phase.

Start an original script without a video or transcript:

```bash
obscript new
obscript new "Minha ideia original" --target-duration 8m --format essay
obscript new "Título do vídeo" --project "Nome da pasta" --vault /path/to/vault
obscript new --dry-run
```

`new` creates a collision-safe project folder containing `script.md`, `project.json`, and `run.yaml`. Open `script.md` in Obsidian or your editor and replace the thesis and narration placeholders. The template uses the existing PT-BR Markdown front matter and includes hook, introduction, development, and conclusion sections. Its defaults are title `Novo roteiro`, format `topics`, and a 10-minute target; `--project` supplies the title when no positional title is given. `--format` accepts `source`, `topics`, or `essay` for this command.

Original projects receive a permanent UUID, timestamps, shared creative-direction path, and `origin: original` / `status: draft` metadata. Their source list is empty. Creation needs neither ytstt nor Codex, does not create a transcripts directory, and does not require the shared creative-direction file to exist. `new` creates the draft only; phase flags and `--into` are rejected with `new`. A dry run creates no files.

After writing the draft, use its printed project ID with the same commands as a transcript project:

```bash
obscript PROJECT_ID                   # import and review your narration
obscript PROJECT_ID --storybook       # review, then plan the visuals
obscript PROJECT_ID --render          # review, plan, then render
```

The original import preserves your narration and section order, deriving structured knowledge and a plan from the draft without transcription or automatic rewriting. Use a `#` title and at least three nonempty `##` sections; replace all template placeholders. Frontmatter supplies the format and positive `target_duration_seconds`, falling back to saved project settings when omitted. An optional `fontes.md` supplies supporting references for review; the imported knowledge is author context, not independent factual evidence. A rejected review leaves the narration for you to edit and exits with status 2. Successful checkpoints are reused on subsequent runs with either harness.

Both workflows produce the same files: storybook planning puts section and scene timestamps in `script.md`, and `script-readable.md` contains plain narration without timings. For original projects, edit either view and rerun your project ID to review the changes and rebuild downstream artifacts. Generated timing cues are excluded from narration on import. Conflicting edits to both views must be synchronized before proceeding. Changes to narration, format, target duration, or `fontes.md` invalidate approval, storybook, render, and post-production output. Re-rendering a scene or polishing requires a current reviewed render; use `--render` first after author edits.

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
obscript PROJECT_ID --storybook 10
obscript PROJECT_ID --render
obscript PROJECT_ID --re-render 005
obscript PROJECT_ID --render --render-batch-size 10
obscript VIDEO --render --opencode
obscript PROJECT_ID --render --opencode
obscript PROJECT_ID --post-production
obscript PROJECT_ID --post-production "Resize Linux logo in scene 25 for a bigger scale."
obscript PROJECT_ID --post-production "001,006,007" "Animation overlaps in these scenes; adjust it."
obscript PROJECT_ID --post-production "001..002" "The transition is abrupt; improve it."
obscript PROJECT_ID --post-production --post-production-batch-size 10
obscript PROJECT_ID --post-production --dry-run
```

`remix` takes two or more comma-separated sources. A playlist URL is accepted as the single remix argument when `ytstt` expands it into at least two videos. A playlist without `remix` produces one independent script per item. `split` takes one non-playlist video. Translation is always conceptual PT-BR normalization during `analyze-source`; there is no `translate` modifier.

A source may be a video URL, playlist URL, local media file, transcript directory, or `.txt`, `.srt`, `.vtt`, or `ytstt` `.json` transcript.

Install cookie support for the workstation's existing `ytstt` once:

```bash
python3 scripts/install-ytstt-auth.py --apply --install-dependencies
```

The installer backs up `ytstt.py` before patching it and installs the versioned authentication adapter beside it. `--install-dependencies` upgrades `yt-dlp[default]` inside ytstt's own virtualenv, including its matching `yt-dlp-ejs` challenge solver scripts. To review the diff, omit both flags; use `--ytstt-home PATH` for another installation. Reapply after a `ytstt` update if needed.

YouTube also requires Node 22+ or Deno 2.3+ on `PATH`. The adapter enables both runtimes, so an existing Node installation can solve YouTube's JavaScript challenges. It shows yt-dlp warnings to make missing runtime or solver dependencies visible. Without these components, valid Firefox cookies can still lead to “The page needs to be reloaded.” See the [yt-dlp JavaScript setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

Obscript always passes `--cookies-from-browser firefox` to ytstt by default. With the adapter installed, Firefox cookies are loaded before the first request, for both URL inspection and audio downloads, including individual playlist items. Sign in to YouTube in Firefox. Reapply the installer above to update an already installed adapter. To choose a browser or profile explicitly:

```bash
obscript 'https://www.youtube.com/watch?v=C3-FIM2xTIw' --render
obscript VIDEO --cookies-from-browser firefox
obscript VIDEO --cookies-from-browser 'chrome:Default'
obscript VIDEO --cookies /path/to/cookies.txt
```

Set `OBSCRIPT_COOKIES_FROM_BROWSER` in your shell to override the default browser. The legacy `auto` selector also uses Firefox from the first request. Use `--cookies-from-browser none` to explicitly disable cookies, or `--cookies FILE` to use an exported file instead. Exported files must use Netscape cookie format. If YouTube rejects the cookies, refresh the browser login and retry; cookies cannot guarantee access against every YouTube restriction.

Without a target, `compress` aims at 60% of the model's recommended/source duration and `extend` at 150%. Without a time controller, the source or model-recommended duration is retained. Use `--dry-run` to validate a command without transcription or agent calls. `--dry-run --render` includes the production stages in the plan and makes no HyperFrames calls or media files.

Without a phase flag, a run stops after script review. `--storybook` continues through visual planning and validation, producing the timestamp-free `script-readable.md`, the timed `script.md`, an Obsidian-readable `storybook.md`, and the structured `storybook.yaml`, without rendering. `--storybook SCENES` requires exactly that many scenes, each allocated approximately `target_duration_seconds / SCENES` seconds; integer-second boundaries distribute any remainder, and the final scene ends exactly at the target. The count must be positive, cannot exceed the target duration in seconds, and cannot be smaller than the approved script's section count because scenes cannot span sections. Repeating `--storybook SCENES` with a different count or timing rebuilds the storybook. `--render` runs any missing script and storybook phases, then creates silent animations through the installed `$hyperframes` skill. These flags are mutually exclusive. Rendering processes at most 20 pending scenes per model iteration by default; `--render-batch-size SCENES` sets another positive limit. The last iteration always processes the remaining scenes and performs final assembly.

Each new project has a permanent UUID in `project.json`, printed before processing starts. Resume with `obscript PROJECT_ID --storybook` or `obscript PROJECT_ID --render`; use the same `--output-dir` or `--vault` as the original run. The project keeps its sources, modifiers, target duration, split settings, and shared direction path. Completed imports, analyses, remix/split results, approved scripts, validated storybooks, and unchanged completed renders are reused. Failed runs keep their checkpoints and ID, including projects that only reached transcript import. Split and independent playlist projects resume each child video in the same project. Running the original source again creates a separate project; ID lookup applies to projects created with this metadata.

For manual visual edits, change the `**Layout:**` paragraph of a scene in `storybook.md`. Rendering uses that paragraph as the controlling scene direction and resolves its Obsidian asset links into verified selected assets. A `## Shared visual system` section in the Markdown supplies project-wide visual direction. Changes to this Markdown invalidate old render output and rebuild the video. If the Markdown changes during a render, the run stops and preserves those edits for the next attempt. `storybook.yaml` remains editable for detailed structured fields, narration references, and timing; it is revalidated before rendering. Invalid asset paths or storybook structure block rendering with an error, leaving edits available for correction. Readable storybooks and script timestamp cues are refreshed from YAML changes when their Markdown has not been manually edited. Reviewed structured script inputs cannot be changed while reusing their old approval.

After a completed render, use `obscript PROJECT_ID --re-render 005` to re-read scene 005 from `storybook.yaml`, replace only that scene's silent render, and reassemble `video.mp4` from all scene outputs. The scene number must exist, and narration, section, timing, shared direction, and every other scene's storybook entry must remain unchanged. A successful rerender archives any older post-production output as stale. If rendering fails, the previous `video.mp4` and scene media are restored. This option requires an existing project with exactly one video and its editable HyperFrames project; split or playlist projects with multiple videos are ambiguous under a single scene number. It is mutually exclusive with `--storybook`, `--render`, and `--post-production`.

Planning and production both read the same shared `Globals/creative-direction.md`; no per-video creative-direction file or visual identity-generation stage is created. Use `--creative-direction FILE` to select another shared file, including when using a different `--output-dir` or `--vault`. The shared file must exist and contain standards or a field template for storybook or render requests; script-only runs and dry runs do not read it. Filled fields are binding; blank fields and suggestions remain unspecified, with execution details resolved in each scene plan. Obscript never edits the shared file. After storybook validation, `script.md` includes section and scene timestamp cues for a human reader. Rendering does not change the approved narration and uses local HyperFrames projects with Node.js 22+, FFmpeg/ffprobe, and the installed HyperFrames skills.

The workflow is script → timed animations → human voiceover and audio editing. Obscript generates no audio, TTS, music, sound effects, or automatic subtitles. Storybook timestamps define the animation timeline and the human recording cues; production never retimes scenes against generated speech.

Each stage uses the selected harness's configured default model. Codex uses `high` reasoning effort by default; override it with `--reasoning-effort`. OpenCode uses its own configured reasoning settings; the Codex reasoning option does not override them. OpenCode model and agent selection is left to the harness unless `--model` is supplied. In OpenCode 2, choosing a model in an interactive session does not change the configured default for new CLI runs; set `model` in `opencode.json(c)` to choose that default ([OpenCode defaults](https://dev.opencode.ai/v2/docs/models/#defaults)). `--model` overrides the model in either harness (OpenCode expects `provider/model`).

`--opencode` applies to every agent stage: analysis, remix/split, duration and format transformations, planning, writing, review, storybook, rendering, rerendering, and post-production. It works with sources and project IDs, for example `obscript PROJECT_ID --post-production --opencode`. Completed checkpoints and verified media are shared between harnesses; pass `--opencode` on any invocation that should use OpenCode, or omit it to use Codex. `--opencode-bin FILE` overrides OpenCode's executable and requires `--opencode`; `--codex FILE` and `--opencode` are mutually exclusive. Dry runs require neither harness to be installed.

## Artifacts

In `storybook.md`, library assets appear as Obsidian preview links such as `[docker](file:///{ref-root}/Globals/assets/tech2-icons/svg/docker.svg)`. Adding one to a scene's Layout makes it a selected render asset. The structured `storybook.yaml` keeps verified absolute paths for its own asset selections. Preview links in either file resolve to absolute library paths for production.

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
script-readable.md         # timestamp-free script, with --storybook or --render
review.yaml
storybook.md              # readable scene plan, with --storybook or --render
storybook.yaml            # detailed structured plan, with --storybook or --render
storybook-review.yaml     # independent per-scene graphical review and researched diagrams
production/               # only with --render
  hyperframes/            # editable composition source and assets; no runtime install
  scenes/scene-001/
    manifest.json
    ...silent rendered scene media...
production.yaml           # only after a render attempt
video.mp4                 # silent animations, only after verified assembly
post-production/          # optional polish pass; source production stays intact
  hyperframes/            # editable source copy with polished effects and transitions
  report.md               # affected scenes, treatments, and visual checks
post-production.yaml      # polish status, source hash, duration, output paths
video-polished.mp4        # verified silent post-production result
run.yaml
project.json              # permanent ID, original command, phase and status
.obscript/                 # exact JSON stage state and prompts
```

A normal run or remix is one production unit. Split runs place `split-plan.yaml` at the project root; each `video-01/`, `video-02/`, and so on owns its knowledge, plan, script, review, visual artifacts, production files, and `.obscript/` state. Independent playlists use the same child layout plus `playlist-plan.yaml`.

Script reviews accept estimated speaking durations within ±30% of the requested target (inclusive). This tolerance applies to narration estimates, not storybook timeline endpoints or rendered-media validation. Other quality checks remain in place, and minor optional improvements alone do not require revision.

If the last script review still requests revision, `script.md` and `review.yaml` remain available and the CLI exits with status 2. No visual stages or rendering run for that unit. Application validation rejects invented, missing, duplicated, or reordered voiceover; unknown or uncovered sections; nonsequential scenes; and gaps, overlaps, or incorrect timeline endpoints. Invalid storybooks are regenerated up to three times, with attempts and validation errors retained in `.obscript/`; continued failure exits with status 1 before production and leaves `storybook.md` marked `status: invalid`, including the last draft and its validation error. Successful plans use `status: validated`.

The approved structured script in `.obscript/approved-script.json` is the sole spoken source. Scenes partition its narration into exact contiguous excerpts, each bound to one section. The shared creative-direction Markdown supplies visual standards to all videos. `storybook.md` links to that source, and `.obscript/creative-direction-source.json` records its absolute path and content hash without copying its standards. `storybook.md` displays an English timeline and a concise Scene / Layout paragraph for each scene: concrete elements, asset references, hierarchy, qualitative spatial relationships, backgrounds, timed explanatory animation, camera focus, and transitions. These production directions describe what appears rather than re-explaining narration. Production resolves geometry and motion measurements from the actual assets and inspected frames; scene plans retain only measurements explicitly required by the user or shared standards, meaningful subject quantities, and useful action timestamps. Narration and on-screen labels keep their original language. Storybook schema 3 requires every scene to resolve five design pillars together: context accuracy, recorded local-asset search and selection, explanatory animation beyond entrances and exits, a semantically mapped visual abstraction, and one mute-readable attention anchor. Validation requires context-relevant foreground library assets or verified reused diagrams in at least `ceil(4n/5)` scenes and verified raster backgrounds from `background1` in at least `ceil(n/5)` scenes; selected paths must be traceable through the scene's structured production fields. An explicit `--storybook` run rebuilds an obsolete storybook contract, while `--render` blocks until that rebuild occurs. `storybook.yaml` retains the complete structured scene fields and exact narration references. `storybook.yaml` remains the structured production plan and is revalidated before rendering. Scene durations primarily fall between 3 and 12 seconds and become the animation's allocated intervals. `voiceover.text` remains the exact human narration reference, not a request to generate speech. The same boundaries appear in `script.md` as `HH:MM:SS.mmm` cues at section and scene level, while `script-readable.md` preserves the approved section-based script without timestamps for comfortable reading. On-screen text supplements narration. Text density is a layout and readability choice, with no fixed word-count limit and no word-count validation gate.

### Independent scene review and diagram references

Each newly generated storybook also receives an independent `$review-storybook` pass before publication. It evaluates the actual visual action against the concept spoken in each scene, rather than trusting the writer's pillar descriptions. Shallow decoration, misleading metaphors, missing mechanisms, and clearly better graphical representations trigger a targeted repair. The reviewer sees compact batches of at most 20 scenes, uses the configured model and application reasoning effort (high by default for Codex), and returns concise findings. Only rejected scenes are rewritten, followed by one research-free recheck. Narration, scene identity, order, and timing cannot change. Unresolved defects block rendering and retain `storybook-review.yaml` and an invalid readable draft; no new validated storybook is published. Successful saved plans are reused without repeating the review. Previously saved plans and manual Layout edits retain their existing reuse behavior; this pass runs when a new plan is generated.

The reviewer may research weak concepts in original documentation, authors' blogs, and papers such as arXiv, grouping related scenes under an instructed budget of three searches and six page/figure opens per batch. Search availability depends on the selected harness/provider; unavailable research does not prevent a concrete scene critique or repair. Useful results record source URLs, explanatory mappings, attribution, and observed reuse terms. The application freezes up to six unique direct raster diagrams per repair batch under `diagram-references/`, reuses downloads by URL, and attaches them to the repair and recheck agents. PNG, JPEG, GIF, and WebP are supported, with a 15-second request timeout and an 8 MiB size limit; HTML, unsupported image formats, and unavailable downloads remain source references rather than blocking the pipeline. Papers or SVG-only figures can still inform an original graphical reconstruction.

Scenes can carry `external_graphics` with local paths, content hashes, provenance, and `reference`, `reuse`, or `animate` directions. Reference-only images inform an original graphic; reuse and animation display the actual figure only with recorded reusable terms or permission. A raster diagram can use staged reveals, masks, highlights, traveling tokens, overlays, or camera focus without requiring editable layers. Verified reused diagrams can satisfy foreground coverage, and the local `background1` quota still applies. Production receives the frozen figures and planned treatment; missing or changed files fail validation. Reports retain the original findings, resolved source references, and repair checks. This review judges the plan; rendered-frame quality remains part of production.

Rendering uses sequential runs of the selected harness through `ProductionAgent`, which invokes `$produce-video` and delegates animation execution to the installed `$hyperframes` skill. Each handoff contains the verbatim shared creative-direction Markdown, its source path, a visual-reference collection, and one bounded storyboard batch with immutable narration references, planned timestamps, and scene output destinations. All iterations resume the same editable project at `production/hyperframes/`; only the final iteration receives the compact all-scene assembly map and final video destination. The producer writes `BRIEF.md` after initialization and extends the project across batches. Defaults are 20 pending scenes per iteration, 1920×1080, and 30 fps; the explicit `--render` request supplies render authorization after required quality checks.

HyperFrames CLI and its prebuilt Studio are installed once per user in `${XDG_CACHE_HOME:-~/.cache}/obscript/hyperframes`, shared by every project and by post-production. Set `OBSCRIPT_HYPERFRAMES_HOME` to use another shared location. The application installs the pinned `hyperframes@0.8.169` before starting the production agent; subsequent batches and projects reuse it without another npm install. An installation lock prevents concurrent runs from installing it twice. Node.js 22+ and npm are required for setup; FFmpeg/ffprobe remain required for rendering and verification. Runtime version changes are managed centrally in `src/obscript/hyperframes_runtime.py`, rather than by upgrading individual compositions.

Use `obscript-hyperframes` (installed by `scripts/install.sh`, or available as `bin/obscript-hyperframes`) for initialization, checks, Studio preview, and renders. It serves any composition from the same shared installation; each composition still has its own editable source and media. For example, from a project's `production/hyperframes/`, run `obscript-hyperframes preview --background` or `obscript-hyperframes check`. The agent handoff supplies this launcher's absolute path, and initialization rewrites generated npm scripts to call it. Do not run project-local npm installs or build Studio in these folders. Existing project scripts are updated when resumed; existing dependency directories are left in place, but post-production copies exclude `node_modules`, Git metadata, and tool caches. Removing old dependency directories is a separate cleanup step.

### Automated source-video visual references

Source projects prepare references after script approval, before `--storybook` planning or `--render` generation. Script-only runs, manual original projects, post-production and single-scene re-renders keep their existing workflows. Re-renders can use references already saved with the production unit.

By default each source gets up to three nonoverlapping 15-second clips and six JPEG frames per clip. OBScript first retrieves metadata with yt-dlp, then downloads at most six four-second video probes. Chapter boundaries and transcript pauses guide these probes, alongside irregular broad coverage. FFmpeg decodes probes at two frames per second into tiny RGB frames; color histograms, spatial color features and adjacent-frame changes guide a greedy diversity selection. Redundant candidates are omitted, so visually repetitive or short sources can yield fewer clips. Representative frames cover the clip, including its strongest measured changes. These are bounded heuristics, not exhaustive scene understanding; fast transitions, small text and subtle camera motion can be missed.

Downloads use [yt-dlp section ranges](https://github.com/yt-dlp/yt-dlp#download-options), force cut keyframes and prefer video streams at or below 480p. FFmpeg normalizes each selected section to a silent MP4 and FFprobe checks its duration. There is no automatic full-video fallback. Network savings depend on the source's seek/range support; a server can require additional data beyond the requested interval. Existing browser or exported-cookie settings are reused. Use accessible sources whose content you are permitted to process; the feature does not bypass DRM or access restrictions. Playlists need the individual video's URL in ingestion metadata (`webpage_url`, `video_url` or `source_url`); otherwise extraction reports that an individual URL is required.

The `analyze-visual-reference` stage attaches frames to the configured Codex or OpenCode model and returns composition/framing, palette/lighting/contrast, camera/graphic motion, typography/text, transitions/rhythm, and animation/effects. Observations must cite an extracted frame and its original timestamp; temporal observations require two distinct frames. Unsupported properties remain `unknown`. The brief cites segments and describes how to adapt supported techniques to new narration. Shared creative standards and manual scene direction remain authoritative. Source footage is reference material and is not inserted into the generated video.

```text
sources/source-01-TITLE/visual-references/
  reference.json                    # source metadata, status, errors, analysis and brief
  processing.log                    # bounded tool diagnostics, with URLs redacted
  FINGERPRINT/
    media.json                      # extraction checkpoint independent of agent analysis
    probe-01.mp4                    # bounded selection probes
    segment-01-000012345.mp4         # segment index and original start in milliseconds
    segment-01-000012345-frame-01.jpg
    *.receipt.json                  # verified section boundaries and media hashes
visual-references.yaml              # per-unit collection, brief and absolute media paths
```

Reference paths inside `reference.json` are relative to its directory. Each frame stores both clip-local and original source seconds. Split units share the same source extraction; remix units receive all participating sources; independent playlist units receive only their own source. Production requests include `visual_references`, and the producer carries the artifact and media paths into HyperFrames `BRIEF.md`.

Successful references are reused when recorded source metadata, transcript timestamps, sampling configuration, analysis skill/schema and file hashes match. This includes usable partial collections with a validated analysis. Remote content is not rechecked on every run. An analysis failure retains the extracted media and retries analysis without downloading it again. Missing or corrupted media invalidates its checkpoint; verified section receipts permit unaffected downloads to be reused. Changed reference collections invalidate render reuse; an explicit `--storybook` rebuilds plans previously created with different references. Rendering retains existing manual scene plans. To force a fresh extraction of changed remote content or retry omitted partial segments, remove that source's `visual-references/` directory before resuming.

Downloads, unavailable videos, absent dependencies, timeouts or an agent without image support record `failed`, `unavailable` or `partial` with actionable errors and continue planning/rendering. `disabled` records an explicit opt-out. Original transcripts without a video URL are still usable. Inspect `reference.json` and `processing.log` for diagnostics.

```bash
obscript VIDEO --storybook
obscript PROJECT_ID --render --visual-reference-clips 3 --visual-reference-duration 15 \
  --visual-reference-frames 6 --visual-reference-probes 6
obscript PROJECT_ID --render --no-visual-references
```

| Option | Default | Allowed range |
| --- | --- | --- |
| `--visual-reference-clips` | 3 | 1–10 |
| `--visual-reference-duration` | 15 seconds | 1–60 |
| `--visual-reference-frames` | 6 per clip | 2–12 |
| `--visual-reference-probes` | 6 | 1–24 |
| `--visual-reference-probe-duration` | 4 seconds | 1–10 |
| `--visual-reference-height` | 480 pixels | 144–720 |
| `--visual-reference-timeout` | 180 seconds per operation | 5–600 |

Use `--yt-dlp`, `--ffmpeg` and `--ffprobe` to override the sampling executables. These overrides apply to reference extraction; the existing production verifier still resolves its own FFprobe. Timeouts stop the downloader and its FFmpeg children on POSIX systems. No additional Python package, database or service is required.

Scene planning and rendering prefer the local visual asset library at `/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets` for general illustrations, technical icons, emojis, raster backgrounds, and textures, including animated interactions. Agents inspect existing files before selecting them and use suitable library assets before inventing SVG foreground artwork, generating images, or searching external stock. Production copies selected assets into its editable project, carries the preference and asset mapping into `BRIEF.md`, and may recolor monochrome fills/strokes or animate icons and internal parts to match the shared direction and scene timing. At least `ceil(total scenes / 5)` scenes, and at least one scene in every nonempty video, visibly use a custom raster image from `background1` as a full-frame or substantial background region rather than only a plain base. These scenes are distributed across the timeline. Background images are evaluated by intrinsic dimensions, aspect ratio, and visible content: sufficiently resolved images can cover the frame, while tiny raster textures are repeated at a suitable scale across a substantial region. Backgrounds and patterns may be rotated, tilted, cropped, or layered, with enough coverage to avoid gaps and preserve foreground readability. SVGs are never generated or used as backgrounds, including SVG files present in a background collection; SVG icons and illustrations remain available as foreground elements. The shared library remains unchanged; explicit assets and meaningful brand or emoji colors are preserved.

The agent writes a durable manifest and silent video for each scene. After the run, the application verifies each scene with ffprobe: it must contain video, contain no audio track, and match its planned duration within one frame. Final assembly places scenes at the exact storybook timestamps and applies visual transitions inside those allocated intervals, preserving the planned total duration. Only a successful run with verified scenes and a verified complete assembly publishes the silent `video.mp4`. `production.yaml` records `backend: hyperframes`, `audio: false`, and `status: complete` or `status: failed`; executor failures still allow verification of completed scenes, preserve partial output, and leave `final_video` empty. The CLI exits with status 1 for production failures.

For example, a human sees this cue in `script.md` and records the exact passage for that animation interval:

```markdown
### scene-001 · 00:00:00.000 → 00:00:03.000

Você observa o padrão.
```

Upstream changes archive stale derivatives under `.obscript/invalidated/`, removing them from current output. A script revision invalidates storybook, production, and the recorded direction reference (archiving legacy per-video direction files when present); a direction change invalidates storybook and production; a storybook change invalidates production. Changes to shared standards require `obscript PROJECT_ID --storybook` to rebuild affected scene plans before rendering; a content-hash check blocks rendering a storybook planned against different standards. Production checks that its upstream inputs remain unchanged and validates the returned scene artifacts before publication. An interrupted render with unchanged inputs retains its editable HyperFrames project and marks verified completed scene media for reuse; changed inputs archive previous production. A completed render is skipped only when its inputs and final video hash still match. There is no automatic filesystem watcher.

`obscript PROJECT_ID --post-production [INSTRUCTION]` runs a separate visual finishing pass on a completed render. The optional quoted instruction is addressed alongside the full standard polish pass. To limit the work, use `--post-production "001,006,007" "INSTRUCTION"` for specific scenes or `--post-production "001..002" "INSTRUCTION"` for the transition from scene 001 to its adjacent scene 002. A target requires an instruction. Scene numbers must exist in the storybook; transition numbers must be adjacent and in ascending order. Selected scenes are batched in storybook order, while a transition is kept in one batch and requires a batch size of at least two. Other scenes and unrelated transitions remain untouched. It requires an existing project ID and is mutually exclusive with `--storybook` and `--render`; `new` does not support it. The pass does not transcribe, rewrite, review, replan, or automatically perform the initial render. It processes at most 20 scenes per model iteration by default; `--post-production-batch-size SCENES` sets another positive limit, and the final partial batch is always processed. Every video in a split or playlist project must have a completed render, and all are checked before polishing begins. Stale approved inputs, changed shared standards or storybooks, missing editable source, changed original video, invalid scene media, or missing ffprobe block the pass. Rebuild changed standards with `--storybook`, then run `--render` before retrying.

The dedicated `$post-production` agent inspects the existing video and edits a copy of `production/hyperframes/` under `post-production/hyperframes/`. Sequential batches resume that same copy and concentrate on flat or poorly polished moments: compatible vignettes and overlay textures, clearer element-focused effects, and varied transitions motivated by adjacent scenes. Each batch retains its own report fragment; after the final batch renders and verifies the complete video, the application combines them into `post-production/report.md`. The pass preserves narration, meaning, shared visual identity, scene order, and every planned boundary.

The application preserves `video.mp4` and the source production project, checks source input hashes after execution, and verifies that the polished assembly contains video, contains no audio, and matches the total duration within one frame. Only a successful pass with a nonempty report publishes `video-polished.mp4`; `post-production.yaml` records completion or failure. Failed runs preserve partial editable work for retry with unchanged source inputs. A verified completed pass is reused while source inputs, polished video, and report hashes match. Source changes archive stale polish output under `.obscript/invalidated/`. Dry runs print only the post-production stages and create no files. One agent run executes each video's complete pass.

Single-batch request and prompt files use the original `post-production` names. Multi-batch runs retain numbered requests and prompts in `.obscript/`, plus numbered responses, executor logs, and report fragments under `post-production/` for inspection.


## Skills

The versioned skill set is:

```text
analyze-source      remix       compress      topics      plan-script
translate-context   split       extend        essay       write-script
review-script       creative-direction       storybook       produce-video
review-storybook
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

Structured-output schemas live in `schemas/`. Reasoning stages use `CodexAgent` with `codex exec --output-schema` in a read-only sandbox; the application writes their returned artifacts. Media execution uses a separate `ProductionAgent` with sequential bounded workspace-write runs rooted at the production directory, no structured-output schema, and network access for HyperFrames dependencies and specified visual assets. This follows the [official Codex sandbox configuration](https://learn.chatgpt.com/docs/security). Single-batch request and prompt files use the original `produce-video` names; multi-batch runs retain numbered requests, prompts, responses, and executor logs for inspection.

With OpenCode, both paths use native [`opencode run --format json --standalone`](https://dev.opencode.ai/v2/docs/cli/commands/#run), sending prompts through stdin and retaining the configured model and agent. OpenCode 2 uses the subprocess working directory and matching `PWD` instead of `--dir`; standalone mode ensures each stage's temporary configuration reaches its private server. Structured stages receive the same schemas in the prompt; the adapter extracts the final assistant message, validates it using the shared validator for obscript's schema keywords, and saves only valid structured checkpoints. Raw events and responses remain in `.obscript/` for inspection. Temporary [OpenCode configuration](https://opencode.ai/docs/config/) adds skill paths and stage permissions without editing user config files. Reasoning permits only reading and searching inputs; the initial storybook reviewer additionally receives websearch and webfetch permissions. The Codex reviewer enables live web search explicitly. Production permits shell execution and limits direct file-edit tools to the requested output directory, blocks nested agents and interactive questions, and retains `executor.log` and `agent-response.txt`. OpenCode's tool permissions do not provide Codex's OS sandbox; shell execution follows the immutable-input prompt and application hash checks used to validate production artifacts.

The tests use a simulated HyperFrames executor, verify exact script-to-scene coverage and human timestamp cues, reject scene and final-duration drift, and exercise real local silent video assembly when FFmpeg tools are available. No live model-driven HyperFrames render runs in the test suite.
