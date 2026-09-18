---
name: creative-direction
description: Consult the shared visual standards for all obscript videos. Use when applying the global creative direction during storybook planning or silent animation production.
---

Read the shared Markdown supplied by the application. The default location is `OUTPUT_DIR/Globals/creative-direction.md`; on this workstation it is `/home/zalmo/documents/obsidian/Videos/Videos/Globals/creative-direction.md`. An explicit `--creative-direction FILE` selects another shared source.

This file is the single source of truth for basic visual standards across videos. Follow every filled field, semantic color rule, typography rule, motion rule, layout rule, and prohibited pattern. Blank fields and field suggestions are unspecified; they are not committed design choices. Resolve the execution details needed for each scene in the storybook, using the approved script's thesis and narrative context. Never establish a new identity for each video or imitate the source video's visual identity.

The approved narration is immutable. On-screen text supplements it and introduces no unsupported facts. Produce silent animations only; a human handles narration and all audio separately. Do not specify TTS, music, sound effects, or automatic subtitles.

Consulting direction is read-only. Do not create a per-video creative-direction Markdown or JSON file, rewrite the shared file, generate media, or invoke HyperFrames during planning. The user maintains the global standards. Editing them is a separate task requiring the user's request. No separate creative-direction generation stage or output schema exists.
