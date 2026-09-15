---
name: analyze-source
description: Analyze video transcripts into a normalized PT-BR knowledge model for the obscript rescripting pipeline. Use for source ingestion and analysis, not final script writing.
---

# Analyze Source

Turn each transcript into a source-independent knowledge model. All explanatory prose in the result must be natural Brazilian Portuguese, even when the source is in another language. Preserve names, quotations needed as evidence, numbers, uncertainty, and technical meaning.

## Build the knowledge layer

- Infer the source title, language, duration, thesis, and communicative objective.
- Identify conceptual topics rather than transcript chapters. For each topic, capture its summary, factual claims, arguments with support, examples, useful tangents, and importance from 0 to 1.
- Record causal, supporting, contrasting, chronological, or prerequisite relationships between topic IDs and preserve the meaningful source order.
- Remove timestamps, greetings, sponsor copy, verbal tics, false starts, and repeated formulations unless repetition carries argumentative meaning.
- Distinguish a source claim from established fact through careful wording. Do not invent missing evidence or silently resolve uncertainty.
- Normalize concepts into PT-BR; do not translate sentence by sentence.

Return only the knowledge object requested by the caller. Do not plan or write narration. When a JSON schema is supplied, follow it exactly.
