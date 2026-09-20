---
name: review-script
description: Independently review an obscript PT-BR video script against its knowledge model, plan, duration, and selected format. Use as the final quality gate, not as the writer.
---

# Review Script

Audit the script independently and return actionable structured findings.

Check:

- factual consistency and unsupported additions;
- coverage of the thesis, required arguments, important facts, and caveats;
- logical continuity and section transitions;
- natural Brazilian Portuguese and spoken rhythm;
- repetition and transcript-like or literal-translation phrasing;
- preservation and purposeful use of the knowledge model's important nuance, including concrete examples, contrasts, caveats, uncertainty, stakes, and surprising details;
- emotional and intellectual progression: the script should create and resolve appropriate curiosity, tension, surprise, complication, or payoff instead of remaining uniformly expository;
- technical explanations that build a mental model, mechanism, consequence, or concrete scenario rather than stacking definitions and attributes;
- an authored voice with varied cadence and meaningful transitions, without generic hype, forced playfulness, or repetitive engagement formulas;
- adherence to `topics`, `essay`, or preserved-source format;
- estimated speaking duration against the target.

Estimate duration from the actual narration at a realistic PT-BR explanatory pace, accounting for punctuation and pauses. Accept estimates within ±30% of the target, including both boundaries: set duration.status to `on_target` and do not report a duration issue or require revision for this variance. Outside this range, use `too_short` or `too_long` and report a high-severity duration issue. Keep the requested target unchanged.

Judge spoken rhythm at a natural pace, not by assuming narration must fit the exact target or each planned section time. When the overall estimate is within tolerance, a section's optimistic timing label alone is not a blocking rhythm defect. Genuine unclear or unnatural narration remains reviewable.

Classify issues by severity and section. Do not fail a script because it lacks a particular joke, rhetorical device, or subjective style preference. Treat localized flat phrasing as low or medium severity; use high severity when pervasive flattening, information-dump structure, or loss of essential nuance makes the script materially less clear, engaging, or faithful to the source. Set the verdict to `pass` when no high-severity issue remains and the script is usable as delivered; minor optional improvements alone do not require revision. On a pass, leave recommendation.rerun empty. Otherwise recommend the smallest stage that should be rerun, normally `write-script`; use `plan-script` when the emotional or explanatory progression itself is structurally flat, and an earlier transformation only for a genuine knowledge-selection defect. Do not rewrite the script in the review.
