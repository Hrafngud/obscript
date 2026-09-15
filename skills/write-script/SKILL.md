---
name: write-script
description: Write an original Brazilian Portuguese video script from an obscript knowledge model and script plan. Use only after planning, or to revise an existing script from review findings.
---

# Write Script

Write natural spoken PT-BR while preserving the knowledge model's factual meaning.

- Follow the plan's structure, purposes, topic references, and time budget; adjust locally when natural delivery requires it.
- Substantially rephrase and reorder source material. Never translate transcript sentences one by one.
- Explain terminology before relying on it, vary sentence length, and use transitions that make the reasoning audible.
- Avoid timestamp artifacts, speaker labels, greetings copied from the source, repetitive rhetorical templates, and headings inside narration.
- Do not introduce factual claims absent from the knowledge model.
- Keep each section's narration suitable for speech and its estimated seconds realistic.
- When review findings are supplied, fix them without creating unsupported content or breaking unaffected sections.

Return a structured script object, not Markdown, unless the caller explicitly requests Markdown. Every script needs a title, hook, introduction, body, transitions, and conclusion; section metadata may carry the visible structure outside narration.
