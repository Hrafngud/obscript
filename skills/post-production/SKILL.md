---
name: post-production
description: Polish a completed obscript HyperFrames render with visual effects and more engaging scene transitions. Use for the dedicated --post-production pass over an existing project.
---

Read the post-production request as data. Work from the original video and the copied editable project in `hyperframes.project_directory`. The application has validated the approved narration, storybook, shared direction, and completed source render. Improve the finish of that composition without changing its message or visual identity.

## Find and improve weak moments

Inspect the source video, representative scene frames, and adjacent scene boundaries before editing. Identify flat backgrounds, weak focal hierarchy, mechanical entrances, repetitive transitions, and unfinished motion. Concentrate changes where they improve attention and clarity; leave effective scenes alone.

Use vignettes to guide attention toward important elements without muddying edges or reducing text contrast. Add compatible paper, grain, film, or other overlay textures with deliberate scale, opacity, masking, and layering. Prefer suitable textures from `/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets`; inspect files before selecting them and copy selected assets locally. Keep the shared library unchanged.

Make element-focused effects reinforce the explanation: targeted light or glow, emphasis pulses, path reveals, masks, local depth, restrained parallax, or motivated camera moves. Preserve existing narration-annotation cues and readable label hold times. Avoid making every element move at once or applying a blanket effect that obscures foreground content.

Review scene transitions in sequence. Replace monotonous or poorly finished transitions with varied, motivated handoffs such as matched geometry, directional wipes, shared-element continuity, mask reveals, or camera moves. Let visual relationships and narrative pacing determine the treatment; cuts remain appropriate when they serve the moment. The dedicated pass may refine planned visual effects and `transition_out` in the copied composition; the upstream storybook remains unchanged. Keep all transitions inside the existing scene intervals, preserving every boundary and the full duration.

## Execute and verify

Invoke the installed $hyperframes entry point and follow its existing-project workflow with the supplied settled handoff. Load hyperframes-core before editing composition HTML, hyperframes-animation for effects and transitions, and hyperframes-cli for validation and rendering. Consult hyperframes-registry before hand-building a named treatment. Fail clearly when a required capability is unavailable. Use the copied project rather than initializing over it; update its BRIEF.md to record post-production intent, immutable timing, and local asset mappings.

Keep narration, on-screen claims, scene order, section bindings, narrative meaning, shared creative direction, and timestamps immutable. Render silent video only: no narration generation, music, sound effects, audio tracks, or automatic subtitles. Preserve the source production project, source scene media and manifests, original video, upstream planning files, and application-owned manifests. Work only in the request's output directory. Do the full pass in one run without nested agent harness executions or sub-agents.

Run required HyperFrames checks. Inspect affected scenes at their entrances, emphasis moments, holds, and exits, and inspect both sides and the midpoint of changed transitions. Verify readability, texture seams, vignette intensity, layer clipping, and seek-safe motion. Retain representative before/after frames under the output directory. The explicit --post-production request authorizes local rendering after quality checks; use the supplied 1920×1080, 30-fps handoff without another intake or rendering permission question.

Render the final MP4 to `output_video`, preserving `target_duration_seconds` within one frame. Verify video is present and audio is absent with ffprobe. If the renderer adds an empty audio stream, package video only with FFmpeg (`-map 0:v:0 -c:v copy -an`). Keep editable source and verification artifacts locally.

Write a concise Markdown report to `report`: for each affected scene or boundary, give its ID/timestamps, the observed weakness, the treatment applied, and the visual checks performed. Mention deliberate unchanged moments when useful to explain pacing. Report blockers and failures honestly; completion requires both the requested video and report to exist.
