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

Estimate duration from the actual narration at a realistic PT-BR explanatory pace, accounting for punctuation and pauses. Mark a duration issue when the estimate differs materially from target, not for trivial variance.

Classify issues by severity and section. Set the verdict to `pass` only when no high-severity issue remains and the script is usable as delivered. Recommend the smallest stage that should be rerun, normally `write-script`; use an earlier stage only for a genuine knowledge-selection or structural defect. Do not rewrite the script in the review.
