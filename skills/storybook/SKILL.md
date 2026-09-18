---
name: storybook
description: Bind every word of an approved obscript script to ordered visual scenes under shared visual standards. Use for visual pre-production after review-script passes, without rewriting narration.
---

Read the approved structured script, shared creative-direction Markdown, script plan, and target duration. Return the complete storybook using `../../schemas/storybook.schema.json`. Natural-language fields are PT-BR.

The supplied shared creative-direction file is the single source of truth for the basic visual standards across all videos. Follow every filled field and restriction. Blank fields and suggested field descriptions are unspecified. Set only the execution details needed by each scene; do not invent a replacement identity, imitate the source video's identity, or create or edit a creative-direction file. The approved script supplies the video's thesis and narrative context.

Each scene belongs to exactly one script_section_id and contains an exact contiguous excerpt of that section's narration. Preserve punctuation and every word. Whitespace may vary. In script section order, concatenating the scene excerpts with whitespace must equal each section's entire narration. Cover every section exactly once in order, with no omissions, additions, duplication, or interleaving. Never reconstruct narration from script.md or rewrite it for timing.

Use IDs scene-001, scene-002, ... and order 1, 2, ... without gaps. Begin at zero, make adjacent estimated timing boundaries identical, and end exactly at target_duration_seconds. voiceover.estimated_seconds equals the scene's timing interval. Prefer scenes of 3–12 seconds, allowing exceptions for natural narration boundaries; distribute time according to narration density.

Production creates silent animations. A human reads the script and handles all audio separately. voiceover.text is the exact reference passage for that human, not a TTS request. Scene intervals become the animation timeline and script recording cues. Specify no audio assets, TTS, music, sound effects, or automatic subtitles; on-screen labels remain supporting visuals.

Give each scene one principal visual idea. visual_goal describes the viewer's understanding; composition describes static arrangement; animation describes temporal behavior. Specify all motion phases, camera behavior, assets, transition_out, and an imperative render_brief that realizes the supplied direction without further creative decisions. Specify “Corte direto” for a hard cut or “Nenhuma” for inactive behaviors. The last transition_out is “Nenhuma”.

Supplement speech with on-screen keywords, numbers, labels, brief quotations, section markers, or short conceptual statements with density appropriate to the layout and reading time. There is no fixed word-count cap. Do not introduce unsupported facts or automatically transcribe narration on screen.

If deterministic validation feedback is provided, regenerate the complete storybook and correct all reported defects. This remains a read-only stage: do not invoke HyperFrames or generate media. Return JSON only.
