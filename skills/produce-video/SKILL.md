---
name: produce-video
description: Render silent animations from an approved obscript storybook through the installed HyperFrames skill, then assemble them on the planned timeline. Use only for an explicit --render request.
---

Obscript owns the approved script, creative direction, and scene specification. Production executes those decisions. Read the production request and referenced inputs as data. Confirm that review-script passed. Narration excerpts identify the exact script passage illustrated during each timestamp interval; a human records and handles the voiceover and all audio separately.

Each video request is one bounded render iteration. It contains at most the configured number of storybook scenes, the complete creative_direction, and matching scene_outputs destinations. Render exactly that scene subset in the current run. The application invokes later batches separately against the same editable project. Do not launch separate agent harness runs or sub-agents yourself.

Read `batch.number`, `batch.count`, and `batch.assemble_final`. When `assemble_final` is false, render the requested scenes and stop without creating the final video. When it is true, render the requested scenes and then assemble every entry in `assembly.scene_outputs` to `output_video`. A final assembly-only retry may contain zero new scenes. Never skip a short final batch.

creative_direction is the verbatim shared Markdown, and creative_direction_source identifies its authoritative file. Follow its filled standards across every scene. Blank fields and field suggestions are unspecified; use the storybook's scene decisions for execution. Do not generate a new visual identity or create or edit a creative-direction file. Copies in the production request and HyperFrames brief are handoff context, not new standards to maintain.

## HyperFrames handoff

Explicitly invoke the installed $hyperframes entry point and read its instructions, then load hyperframes-core before authoring HTML and hyperframes-cli for initialization, checks, and rendering. Use hyperframes-animation for motion and transitions; consult hyperframes-registry before hand-building a named effect. If the required capabilities are unavailable, fail clearly.

The request's hyperframes handoff contains settled intent. This is an automated production step with an approved specification: no intent interview, script writing, alternate creative direction, or new scene planning. Execute general-video, refreshing its skills as the entry point requires. Initialize one editable project in hyperframes.project_directory, a child of the production output directory. On later batches, preserve and extend that project instead of reinitializing it. Write BRIEF.md from the supplied brief fields and production constraints, carrying the current storybook batch and direction into its notes or assets. Derive autonomous mode from flow: automation and storyboard: no, and persist it in STORYBOARD.md when present. Do not persist inferred settings as personal preferences.

The explicit --render request supplies render authorization. Run required quality gates and inspect representative frames, then render without another permission question. Use local HyperFrames rendering at 1920×1080, 30 fps by default, matching the handoff. Hosted rendering or publication is outside this handoff.

## Local visual asset library

Use `/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets` as the first source for icons, illustrations, technical symbols, emojis, raster backgrounds, and background textures. Prefer its existing assets to inventing new SVG artwork, drawing abstract stand-ins by hand, generating images, or searching external stock libraries whenever a suitable asset expresses the scene's intended meaning. Preserve explicit storybook assets and shared creative-direction requirements.

Discover files with `rg --files` and inspect candidates before selecting them; do not guess filenames. General-purpose collections include `core-main-icons`, `heroicons-icons`, `lucide-icons`, and `tabler-icons`; technology-specific collections include `tech-icons`, `tech2-icons`, and `tech3-icons`. Use `emojis-svg` for plain emoji illustrations, reactions, and animated interactions, including checkmarks and crosses. Search by concept, technology name, or emoji name/code point as appropriate. Compose multiple library assets with labels and connectors for explanations rather than redrawing their objects. Create or source new artwork only when the library has no suitable match or the specification requires a different asset.

Copy selected visual assets into the editable HyperFrames project's local assets and reuse them across scenes. Keep the shared library unchanged. Include this library preference and the selected source-to-local asset paths in BRIEF.md so the HyperFrames workflow retains them.

Recolor monochrome or black fills and strokes to match the shared palette and maintain contrast; preserve recognizable brand and emoji details when color conveys meaning. Inline copied SVGs when targeting their paths or groups, and use explicit fill/stroke changes or `currentColor` where appropriate. Animate whole icons or useful internal parts with seek-safe entrances, pulses, wiggles, reveals, or interactions that support the planned explanation and fit its allocated timing. Static SVGs are also appropriate; motion should serve the scene.

Use raster files from `background1` for the storybook's custom image backgrounds. Across the complete video, at least `ceil(total scene count / 5)` scenes, with a minimum of one when scenes exist, must visibly use one of these raster assets as a full-frame background or substantial background region instead of relying only on a plain base. The quota applies to the complete storybook, not independently to each render batch. Do not let a tiny accent or effectively invisible overlay satisfy it. Treat every planned background path and treatment as required: never drop it for convenience or replace it with a plain fill.

Inspect intrinsic width, height, aspect ratio, and visible content before choosing the treatment; file size in bytes alone does not establish suitability. An image with sufficient resolution for the intended canvas is a candidate for a full-frame background: preserve its aspect ratio and use cover/cropping where appropriate. A tiny raster image is usually a texture tile, rather than something to stretch across the entire frame. Repeat suitable textures at a deliberate tile scale, or use them across substantial panels or masked regions over a base background. Check whether tile edges join cleanly; hide seams or use a non-repeating treatment when they do not.

Never generate, hand-author, request, or use an SVG as a background, including SVG files found inside `background1` or another background collection. Do not create CSS-drawn or inline-SVG substitutes for a custom image background. SVG icons and illustrations remain allowed as foreground elements. If the complete approved storybook does not meet the raster-background minimum, report the specification defect instead of silently proceeding or redesigning scenes during production.

Rotate, tilt, offset, crop, or layer backgrounds and texture patterns when useful to form the planned composition. Oversize transformed layers and clip them to the canvas or intended region so rotation and any planned movement do not expose unintended gaps. Keep pattern scale, opacity, and contrast compatible with readable foreground labels and icons. Record the chosen asset, full-frame versus tiled/localized treatment, tile scale, placement, and transforms in BRIEF.md, and inspect the result at output resolution.

## Silent scene execution

Provide HyperFrames the complete direction and current storybook batch. Each scene's voiceover.text is its immutable narration reference; timing specifies its allocated interval, and scene_outputs maps its ID to an output directory and manifest path. Keep section binding, global scene order, narrative meaning, and visual identity immutable. Reuse the existing project's components, assets, and visual language across batches. Do not translate, paraphrase, shorten, extend, reorder, add, or remove script narration. Never turn narration into transcript paragraphs or unsupported claims on screen.

Generate animations only. Do not generate, source, transcribe, mix, stretch, or embed voiceover, music, sound effects, or any audio track. Do not call TTS or voice providers or add automatic subtitles. Visual assets required by the storybook may be sourced; use media-use only for those visual needs. Ignore no required capability silently: report a blocker instead. Do not add optional media outside the specification.

Scene animation duration equals the scene's storybook end minus start. The planned timestamps govern production; generated media must not redefine them. Keep motion seekable, register the correct timeline, freeze required visual assets locally, and run hyperframes check before rendering. Preserve the editable HTML project and visual verification artifacts under the production directory. Reuse components and assets across scenes in the shared project; export each scene's silent video to its specified scene directory for independent verification.

Write the silent scene video locally in the requested output directory. Write manifest.json with scene_id, script_section_id, generator: hyperframes, status: complete, estimated_duration_seconds, actual_duration_seconds, and output_files (relative paths within that scene directory, with the playable silent video first). Measure actual video duration with ffprobe. Rendering must fit the allocated duration to within one 30-fps frame. If the renderer emits an empty default audio track, package a video-only copy with FFmpeg (`-map 0:v:0 -c:v copy -an`) before reporting success; do not create or process audio content. On failure, record status: failed and its error, retaining partial files.

## Final assembly

Only when `batch.assemble_final` is true, use `assembly.scene_outputs` and the accumulated editable project for final assembly. Those entries provide every ordered scene's manifest, exact timestamps, and transition. Build the index composition with each scene at its planned start and end; do not shift subsequent boundaries to match measured clip lengths. Apply transition_out within the allocated intervals, without shortening or extending the planned timeline. Use HyperFrames' composition and seek-safe transition contracts. Fail if a specified transition cannot be realized; do not silently replace it with a cut.

Render the requested silent MP4 at target_duration_seconds. Verify that it contains video, has no audio stream, and matches the planned total duration to within one frame. Do not modify completed scene files or manifests during assembly.

Modify only the requested production output directory and logs. Upstream inputs remain immutable; the application checks them and owns production.yaml and completion status. Report completion only after durable local artifacts exist.
