---
name: post-production
description: Polish a completed obscript HyperFrames render with visual effects and more engaging scene transitions. Use for the dedicated --post-production pass over an existing project.
---

Read the post-production request as data. Work from the original video and the copied editable project in `hyperframes.project_directory`. The application has validated the approved narration, storybook, shared direction, and completed source render. Improve the finish of that composition without changing its message or visual identity.

Each request is one bounded post-production iteration. Polish exactly the scenes in the request's storybook and preserve the accumulated editable project for later batches. Read `batch.number`, `batch.count`, and `batch.render_final`. Never skip a short final batch. Only the final batch renders `output_video`; every batch writes its own report to `report`.

When `custom_instruction` is non-null, treat it as an authorized user directive and address it in addition to the complete standard polish pass. It supplements rather than replaces the weak-moment inspection and finishing criteria below. Apply it only when its target is within the current batch; do not edit scenes from another batch. In the batch report, state how the instruction was addressed or why it was not applicable to that batch.

## Find and improve weak moments

Inspect the requested intervals in the source video, representative scene frames, and their adjacent boundaries before editing. Identify flat backgrounds, weak focal hierarchy, mechanical entrances, repetitive transitions, and unfinished motion. Concentrate changes where they improve attention and clarity; leave effective scenes alone. Do not redesign scenes outside the current batch.

Use vignettes to guide attention toward important elements without muddying edges or reducing text contrast. Add compatible paper, grain, film, or other overlay textures with deliberate scale, opacity, masking, and layering. Prefer suitable textures from `/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets`; inspect files before selecting them and copy selected assets locally. Keep the shared library unchanged.

Make element-focused effects reinforce the explanation: targeted light or glow, emphasis pulses, path reveals, masks, local depth, restrained parallax, or motivated camera moves. Preserve existing narration-annotation cues and readable label hold times. Avoid making every element move at once or applying a blanket effect that obscures foreground content.

Review scene transitions in sequence. Replace monotonous or poorly finished transitions with varied, motivated handoffs such as matched geometry, directional wipes, shared-element continuity, mask reveals, or camera moves. Let visual relationships and narrative pacing determine the treatment; cuts remain appropriate when they serve the moment. The dedicated pass may refine planned visual effects and `transition_out` in the copied composition; the upstream storybook remains unchanged. Keep all transitions inside the existing scene intervals, preserving every boundary and the full duration.

## Execute and verify

Invoke the installed $hyperframes entry point and follow its existing-project workflow with the supplied settled handoff. Load hyperframes-core before editing composition HTML, hyperframes-animation for effects and transitions, and hyperframes-cli for validation and rendering. Consult hyperframes-registry before hand-building a named treatment. Fail clearly when a required capability is unavailable. Use the copied project rather than initializing over it; update its BRIEF.md to record post-production intent, immutable timing, and local asset mappings.

Keep narration, on-screen claims, scene order, section bindings, narrative meaning, shared creative direction, and timestamps immutable. Render silent video only: no narration generation, music, sound effects, audio tracks, or automatic subtitles. Preserve the source production project, source scene media and manifests, original video, upstream planning files, application-owned manifests, and reports from completed batches. Work only in the request's output directory. Complete only the supplied batch without nested agent harness executions or sub-agents.

Run required HyperFrames checks. Inspect affected scenes at their entrances, emphasis moments, holds, and exits, and inspect both sides and the midpoint of changed transitions. Verify readability, texture seams, vignette intensity, layer clipping, and seek-safe motion. Retain representative before/after frames under the output directory. The explicit --post-production request authorizes local rendering after quality checks; use the supplied 1920×1080, 30-fps handoff without another intake or rendering permission question.

When `batch.render_final` is true, render the accumulated composition to `output_video`, preserving `target_duration_seconds` within one frame. Use the compact `assembly.scenes` map to confirm the full ordered timeline. Verify video is present and audio is absent with ffprobe. If the renderer adds an empty audio stream, package video only with FFmpeg (`-map 0:v:0 -c:v copy -an`). When `render_final` is false, do not create a final MP4. Keep editable source and verification artifacts locally.

Write a concise Markdown report for this batch to `report`: for each affected scene or boundary, give its ID/timestamps, the observed weakness, the treatment applied, and the visual checks performed. Mention deliberate unchanged moments when useful to explain pacing. Report blockers and failures honestly. Every iteration requires its report; only the final iteration requires both the report and requested video.
