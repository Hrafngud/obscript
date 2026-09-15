---
name: plan-script
description: Convert a transformed obscript knowledge model into a timed PT-BR script plan. Use after pipeline, time, and format transformations and before narration writing.
---

# Plan Script

Plan how the retained knowledge will become a spoken video without writing the narration itself.

- Define an original title, thesis, hook idea, and section sequence.
- Give every section a purpose, type, topic references, transition intent, and estimated seconds.
- Allocate time according to argumentative importance and explanation difficulty.
- Make total estimated seconds closely match the requested target duration.
- For `topics`, favor modular body sections with explicit connective transitions.
- For `essay`, ensure sections form a cumulative argument with a complication or counterpoint where supported.
- For default source format, preserve the source's useful organization while replacing transcript artifacts with script structure.
- Put the hook in the dedicated hook field, then include introduction, body, and conclusion sections. Do not draft their spoken wording.

Return only the plan object requested by the caller.
