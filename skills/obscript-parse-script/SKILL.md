---
name: obscript-parse-script
description: Interpret inline obscript script markup as approximate word-synchronized motion cues for Storybook elements. Use when planning or updating a storybook from italic, bold, inline-code, strikethrough, or %%comment%% annotations; do not rewrite narration or render video.
---

# Parse Script Motion Cues

Read the approved structured script and the storybook scene plan, or apply these rules while creating that plan. Use the existing scene intervals and shared creative direction. Write scene instructions in English; preserve approved narration, quoted cue phrases, on-screen labels, IDs, and asset paths in their original form. This is visual pre-production: return a storybook conforming to [the existing schema](../../schemas/storybook.schema.json), without invoking HyperFrames or generating media.

Treat inline formatting around a spoken word or phrase as an instruction for the visual element it names. The delimiters are motion annotations, not spoken words or automatic on-screen labels. Preserve the approved narration, including its markup, verbatim in `voiceover.text`; strip delimiters only in a temporary reading copy used for word counting and target matching. Strikethrough and comments still contain spoken words; do not delete their contents.

If a separately supplied annotated script has plain narration in the approved structured script, accept its cues only where the words and their section/order match the approved narration after removing motion delimiters. Do not use headings or other Markdown scaffolding as cues or replace the approved script with that copy. With no matching annotations, retain the existing scene behavior.

## Markup and behavior

| Inline annotation | Motion on the named element | Suggested execution |
| --- | --- | --- |
| `*element*` or `_element_` | Zoom in, then out | Scale the element from 1 to 1.12 and back to 1 over 0.8 seconds, centered on itself. |
| `**element**` or `__element__` | Wiggle for a while | Rotate around its center between approximately −4° and +4° for three oscillations over 1.2 seconds, then settle at the original rotation. |
| `` `element` `` | Pulse | Scale from 1 to 1.08 and back twice over 0.8 seconds. |
| `~~element~~` | Red overlay and an X emoji above it | Fade in a translucent red overlay confined to the element and a ❌ directly above it; hold for approximately 1 second, then fade both out. |
| `%%element%%` | Green overlay and a V-shaped checkmark emoji above it | Fade in a translucent green overlay confined to the element and a ✅ directly above it; hold for approximately 1 second, then fade both out. |

These values are starting points, not fixed requirements. Fit motions inside the scene, retain legibility, and restore the element's original transform and appearance afterward. Zoom acts on the element; leave the scene camera unchanged unless the scene already requires camera motion. Keep overlays translucent so the element stays recognizable, and place the emoji above its bounds without clipping. The positive comment cue uses green; the negative strikethrough cue uses red.

Recognize complete, nonempty inline spans. Resolve bold delimiters before italic delimiters so `**element**` does not produce an extra zoom. Treat inline-code contents literally: formatting inside backticks does not generate additional cues. Ignore escaped delimiters, fenced code blocks, unmatched markers, and underscores inside ordinary words. For nested formatting outside code, retain the explicit cues and stagger conflicting transforms briefly; do not multiply the same cue for the same span.

## Bind each occurrence to an element

Resolve the marked phrase to an existing `visual_elements` entry using its content, role, and scene context. A cue may refer to an object, diagram part, icon, or existing text label. Give its target an unambiguous description in the animation instructions; repeating the same phrase later creates a separate timed cue, not a match to its first occurrence.

During initial scene planning, include the named element when the narration and visual idea support it. When updating an existing storybook, preserve its structure and unrelated decisions. If a target is ambiguous or absent, state the unresolved cue and its phrase in `render_brief` instead of silently animating a different element or inventing an unsupported object. Do not turn every marked phrase into on-screen text.

Keep each marked phrase wholly within one scene when planning boundaries. For an existing boundary that splits a phrase, anchor the cue to its first word in the scene containing that word and confine the effect to that interval; note any missing target as above. Never duplicate or move narration to fit an effect.

## Approximate synchronization

Use caller-supplied word timestamps when available and consistent with the scene timeline. Otherwise estimate from the exact scene excerpt after removing motion delimiters:

- Let `N` be its spoken word count, using whitespace-separated words; punctuation attached to a word does not add another word.
- Let `k` be the zero-based position of the marked phrase's first word in that excerpt. Track occurrences in order rather than searching for the first matching string.
- For a scene starting at `S` and ending at `E`, estimate the absolute cue time as `S + (k / N) * (E - S)`. The scene-local time is the absolute cue time minus `S`.
- Begin the effect at that estimate. Allow longer marked phrases a longer hold when useful, but clamp every effect's end to `E`. Shorten repetitions near the boundary rather than extending the scene or moving later scenes. No marks means no added effects.

Label these times as estimated; equal word spacing approximates a human reading and does not guarantee alignment with a later recording. Do not generate speech, transcribe audio, or retime the approved scene intervals to improve the estimate.

Record each resolved cue in `animation.emphasis` with the marked phrase/occurrence, target, effect, estimated scene-local start/end, and absolute start/end. Add the corresponding imperative execution instruction to `render_brief`, preserving its existing content. Use these existing string fields; do not add cue keys to the schema. Retain entrance, continuous behavior, exit, and camera decisions unless they conflict with the explicit cue; stagger or shorten motions on the same target to make both intentions clear.

For example, a scene from 10 to 16 seconds with `Veja o *círculo* e a **seta**.` has six spoken words. The circle cue begins at approximately 12 seconds (scene-local 2 seconds), and the arrow cue at approximately 15 seconds (scene-local 5 seconds). Fit the arrow's wiggle into the remaining second. A suitable emphasis instruction is: "At the occurrence of 'círculo', scale the circle from 1 to 1.12 and back between scene-local 2.00–2.80 s (absolute 12.00–12.80 s, estimated). At the occurrence of 'seta', wiggle the arrow by ±4° and restore its rotation between scene-local 5.00–6.00 s (absolute 15.00–16.00 s, estimated)."

Before returning the complete storybook, check that every recognized cue is resolved or explicitly noted, its timestamps stay inside its scene, and narration coverage, scene order, and total duration remain unchanged. Return JSON only when called by the obscript storybook stage.
