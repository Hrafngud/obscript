---
name: write-script
description: Write an original Brazilian Portuguese video script from an obscript knowledge model and script plan. Use only after planning, or to revise an existing script from review findings.
---

# Write Script

Write natural spoken PT-BR while preserving the knowledge model's factual meaning and its most valuable nuance. The result should feel authored and alive, not like a spoken outline or a compressed encyclopedia entry.

- Follow the plan's structure, purposes, topic references, and time budget; adjust locally when natural delivery requires it.
- Substantially rephrase and reorder source material. Never translate transcript sentences one by one.
- Treat the knowledge model as a reservoir, not a checklist. Select and develop the details that make the thesis land; do not flatten examples, caveats, contrasts, implications, uncertainty, or surprising observations into generic summary sentences merely to mention every available fact.
- Give the script an emotional and intellectual contour appropriate to the material. Build and release curiosity, tension, surprise, recognition, complication, or payoff across sections. Never fabricate stakes or force jokes, sentiment, or exaggerated drama.
- Explain technical ideas through a usable mental model: show what changes, what acts on what, why it matters, or what someone would observe in a concrete scenario. Introduce terminology after the listener has something to attach it to. Prefer one developed explanation or example over a dense definition followed by a list of attributes.
- Vary sentence length, cadence, and rhetorical shape. Mix crisp turns with room for an idea to unfold; use questions, callbacks, contrast, understatement, or playful phrasing only where they sound natural. Avoid long runs of equally weighted declarative sentences.
- Make transitions carry thought and momentum. Each section should inherit a question, consequence, image, or tension from the previous one instead of announcing a new heading.
- Allow a distinct point of view and human presence without copying the source speaker's verbal tics. Preserve source-supported wit, skepticism, wonder, urgency, or warmth when it helps the explanation.
- Earn the conclusion through synthesis, consequence, or a callback to the opening. Do not merely repeat the thesis and section summaries.
- Avoid timestamp artifacts, speaker labels, greetings copied from the source, repetitive rhetorical templates, and headings inside narration.
- Avoid generic engagement formulas such as repeated “mas aqui está o ponto”, “imagine que”, or artificial cliffhangers. Playfulness must sharpen meaning or rhythm, not decorate every paragraph.
- Do not introduce factual claims absent from the knowledge model.
- Keep each section's narration suitable for speech and its estimated seconds realistic.
- When review findings are supplied, fix them without creating unsupported content or breaking unaffected sections.

Return a structured script object, not Markdown, unless the caller explicitly requests Markdown. Every script needs a title, hook, introduction, body, transitions, and conclusion; section metadata may carry the visible structure outside narration.
