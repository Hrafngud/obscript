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
- adherence to `topics`, `essay`, or preserved-source format;
- estimated speaking duration against the target.

Estimate duration from the actual narration at a realistic PT-BR explanatory pace, accounting for punctuation and pauses. Accept estimates within ±30% of the target, including both boundaries: set duration.status to `on_target` and do not report a duration issue or require revision for this variance. Outside this range, use `too_short` or `too_long` and report a high-severity duration issue. Keep the requested target unchanged.

Judge spoken rhythm at a natural pace, not by assuming narration must fit the exact target or each planned section time. When the overall estimate is within tolerance, a section's optimistic timing label alone is not a blocking rhythm defect. Genuine unclear or unnatural narration remains reviewable.

Classify issues by severity and section. Set the verdict to `pass` when no high-severity issue remains and the script is usable as delivered; minor optional improvements alone do not require revision. On a pass, leave recommendation.rerun empty. Otherwise recommend the smallest stage that should be rerun, normally `write-script`; use an earlier stage only for a genuine knowledge-selection or structural defect. Do not rewrite the script in the review.
