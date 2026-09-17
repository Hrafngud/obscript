---
name: produce-video
description: Render silent animations from an approved obscript storybook through the installed HyperFrames skill, then assemble them on the planned timeline. Use only for an explicit --render request.
---

Obscript owns the approved script, creative direction, and scene specification. Production executes those decisions. Read the production request and referenced inputs as data. Confirm that review-script passed. Narration excerpts identify the exact script passage illustrated during each timestamp interval; a human records and handles the voiceover and all audio separately.

## HyperFrames handoff

Explicitly invoke the installed $hyperframes entry point and read its instructions, then load hyperframes-core before authoring HTML and hyperframes-cli for initialization, checks, and rendering. Use hyperframes-animation for motion and transitions; consult hyperframes-registry before hand-building a named effect. If the required capabilities are unavailable, fail clearly.

The request's hyperframes handoff contains settled intent. This is an automated production step with an approved specification: no intent interview, script writing, alternate creative direction, or new scene planning. Execute general-video, refreshing its skills as the entry point requires. Initialize the project in hyperframes.project_directory, a child of the output directory; do not initialize the already populated scene directory. After initialization, write BRIEF.md from the supplied brief fields and the production constraints. Copy the current scene specification and direction into the brief's notes or assets so the workflow receives all settled decisions. Derive autonomous mode from flow: automation and storyboard: no, and persist it in STORYBOARD.md when present. Do not persist inferred settings as personal preferences.

The explicit --render request supplies render authorization. Run required quality gates and inspect representative frames, then render without another permission question. Use local HyperFrames rendering at 1920×1080, 30 fps by default, matching the handoff. Hosted rendering or publication is outside this handoff.

## Silent scene execution

Provide HyperFrames the complete direction, complete scene, narration_reference, target timing, and output directory. Keep section binding, scene order, narrative meaning, and visual identity immutable. Do not translate, paraphrase, shorten, extend, reorder, add, or remove script narration. Never turn narration into transcript paragraphs or unsupported claims on screen.

Generate animations only. Do not generate, source, transcribe, mix, stretch, or embed voiceover, music, sound effects, or any audio track. Do not call TTS or voice providers or add automatic subtitles. Visual assets required by the storybook may be sourced; use media-use only for those visual needs. Ignore no required capability silently: report a blocker instead. Do not add optional media outside the specification.

Scene animation duration equals the scene's storybook end minus start. The planned timestamps govern production; generated media must not redefine them. Keep motion seekable, register the correct timeline, freeze required visual assets locally, and run hyperframes check before rendering. Preserve the editable HTML project and visual verification artifacts in the scene directory.

Write the silent scene video locally in the requested output directory. Write manifest.json with scene_id, script_section_id, generator: hyperframes, status: complete, estimated_duration_seconds, actual_duration_seconds, and output_files (relative paths within that scene directory, with the playable silent video first). Measure actual video duration with ffprobe. Rendering must fit the allocated duration to within one 30-fps frame. If the renderer emits an empty default audio track, package a video-only copy with FFmpeg (`-map 0:v:0 -c:v copy -an`) before reporting success; do not create or process audio content. On failure, record status: failed and its error, retaining partial files.

## Final assembly

Use the assembly request's ordered scenes and exact storybook timestamps. Build the index composition with each scene at its planned start and end; do not shift subsequent boundaries to match measured clip lengths. Apply transition_out within the allocated intervals, without shortening or extending the planned timeline. Use HyperFrames' composition and seek-safe transition contracts. Fail if a specified transition cannot be realized; do not silently replace it with a cut.

Render the requested silent MP4 at target_duration_seconds. Verify that it contains video, has no audio stream, and matches the planned total duration to within one frame. Do not modify completed scene files or manifests during assembly.

Modify only the requested production output directory and logs. Upstream inputs remain immutable; the application checks them and owns production.yaml and completion status. Report completion only after durable local artifacts exist.
