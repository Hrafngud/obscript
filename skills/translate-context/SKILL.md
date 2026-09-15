---
name: translate-context
description: Normalize non-Portuguese concepts and terminology into natural Brazilian Portuguese inside an obscript knowledge model. Use for imported or partially untranslated knowledge, not sentence-by-sentence transcript translation.
---

# Translate Context

Convert the conceptual layer, not the surface wording. Preserve factual meaning, proper nouns, values, citations, uncertainty, and established technical terms.

- Prefer idiomatic PT-BR that would sound natural in spoken explanation.
- Explain or adapt idioms whose literal version would be awkward.
- Keep a foreign term when that is the conventional Brazilian usage; briefly introduce it when comprehension requires context.
- Do not localize examples, institutions, units, or claims in ways that change their meaning.
- Do not add a Brazilian example unless the caller explicitly asks for extension or localization.
- Do not produce narration. Return the same knowledge structure with normalized PT-BR prose.

This is an internal repair/import skill. In the normal obscript flow, `analyze-source` already creates the canonical PT-BR knowledge model, so no public `translate` command is needed.
