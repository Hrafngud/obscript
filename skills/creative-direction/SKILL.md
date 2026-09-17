---
name: creative-direction
description: Establish one original visual direction from an approved obscript structured script and its knowledge and plan. Use after review-script passes, before storybook planning.
---

Create one committed visual identity for the finished video. Read the supplied knowledge, plan, approved structured script, target duration, format, and pipeline type. Return the complete structured direction using `../../schemas/creative-direction.schema.json`.

The approved narration is immutable. Do not translate, paraphrase, shorten, extend, reorder, add, or remove spoken content. Do not reconstruct narration from script.md. Never imitate the source video's visual identity; source metadata supplies narrative context only.

The deliverable is silent animations aligned to narration timestamps. A human records and handles all audio separately. Do not specify audio production, TTS, music, sound effects, or voice selection.

Choose specific composition, palette, typography, motion, layout, motifs, section treatments, continuity rules, and prohibited patterns that express the script's thesis. Every field commits to one decision: no alternatives, tentative choices, or menus. Define enough detail for a producer to execute without selecting another direction. Natural-language fields are PT-BR.

On-screen text supplements narration with keywords, numbers, labels, brief quotations, section markers, and short conceptual statements. Choose text density for the composition and available reading time, with no fixed word-count cap. Prefer clear, readable text and introduce no new factual claims. Set the subtitle policy to no automatic subtitles. Use semantic color rules and predictable emphasis to keep the visual hierarchy coherent.

This is a read-only planning stage. Do not invoke HyperFrames or generate media. Return JSON only; the application preserves it and renders creative-direction.md.
