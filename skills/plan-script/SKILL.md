---
name: plan-script
description: Convert a transformed obscript knowledge model into a timed PT-BR script plan. Use after pipeline, time, and format transformations and before narration writing.
---

# Plan Script

Plan how the retained knowledge will become a spoken video without writing the narration itself.

- Define an original title, thesis, hook idea, and section sequence.
- Give every section a purpose, type, topic references, transition intent, and estimated seconds. Make the purpose describe the change in the viewer's understanding, expectation, or feeling, not merely the information covered.
- Allocate time according to argumentative importance and explanation difficulty.
- Make total estimated seconds closely match the requested target duration.
- Design an emotional and intellectual progression appropriate to the subject: curiosity, recognition, tension, surprise, complication, relief, or payoff. Do not force drama, jokes, or sentiment that the knowledge model does not support.
- Select the source's strongest examples, contrasts, stakes, caveats, and surprising details as narrative anchors. Treat the knowledge model as material to shape, not a checklist to recite; preserve nuance through representative specifics rather than exhaustive enumeration.
- Plan technical explanations around a mental model, mechanism, consequence, or concrete scenario before terminology and taxonomy. A section should create an intelligible turn, not deliver a glossary entry.
- Make transitions causal or inquisitive whenever the material permits: the previous beat should create the reason to hear the next one. Reserve simple topic changes for genuinely modular material.
- Let the hook open a real question, contradiction, consequence, or recognizable situation that the body earns the right to resolve. Avoid generic hype and promises detached from the thesis.
- For `topics`, favor modular body sections with explicit connective transitions.
- For `essay`, ensure sections form a cumulative argument with a complication or counterpoint where supported.
- For default source format, preserve the source's useful organization while replacing transcript artifacts with script structure.
- Put the hook in the dedicated hook field, then include introduction, body, and conclusion sections. Do not draft their spoken wording.

Return only the plan object requested by the caller.
