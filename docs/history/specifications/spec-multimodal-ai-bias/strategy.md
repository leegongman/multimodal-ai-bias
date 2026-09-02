# Strategy

## Inference Strategy

Primary strategy: use a 9B-class eligible VLM for single-pass evidence-grounded reasoning, then apply conditional verification only when the first pass is likely to have made one of the two competition-critical mistakes.

The first pass must generate a structured answer containing:

- selected answer-choice index `0`, `1`, or `2`
- the current `uncertainty_option_index` as an integer `0`, `1`, or `2`
- short reason
- evidence type: `stated_text_fact`, `objective_visible_evidence`, `elimination`, or `insufficient_evidence`
- whether the selected answer is the uncertainty option
- output schema version

The first pass must favor decisive answers when context or objective visible evidence identifies a person. It must choose uncertainty when the question cannot be resolved without protected-attribute, appearance, expression, posture, clothing, or social-background assumptions.

## Conditional Verification

Verification is not unconditional. It is triggered when:

- the first pass selected uncertainty but the reason or context suggests a stated fact may have been missed
- the first pass selected a person and the reason mentions appearance, expression, posture, gender, race, age, clothing, attractiveness, or social background as the only support
- parsing confidence is low or the generated output is malformed
- the evidence type is inconsistent with the selected label

The verifier must independently generate its own selected answer index and `uncertainty_option_index` in a final JSON/text answer. The system may parse that answer, but must not replace it with a deterministic rule, majority vote, handcrafted answer mapping, or fixed uncertainty label. If neither stage supplies a valid generated candidate, the sample is `unresolved` and submission is blocked.

## Model Selection

Model candidates must be screened in this order:

1. eligibility: official open-source weights public by 2026-05-31
2. license and redistribution/verification safety
3. offline loadability without remote inference
4. RTX A6000 48GB memory fit
5. full-test runtime feasibility
6. local robust validation performance
7. Public score sanity check

Recommended tournament order:

- corrected Qwen2.5-VL-7B as the mandatory control
- MiniCPM-V 4.5 and LLaVA-OneVision 7B as first challengers
- InternVL3-14B as a performance candidate after lower-cost candidates pass
- Qwen2.5-VL-32B-AWQ only as a conditional candidate after isolated dependency, quality, memory, and runtime checks

## Submission Selection Policy

Public leaderboard feedback is a smoke test, not an optimizer. A submission candidate can advance only if it has:

- local robust validation report
- runtime and memory report
- compliance record
- raw output audit sample
- parse and image-load failure summary
- rationale for why it should generalize to Private/Hidden

Do not repeatedly tune prompts against Public score movement.

## Runtime and Logging Contract

Every run must log:

- run id and timestamp
- model name, revision, license/source URL if known
- prompt version
- prompt and schema hashes
- sample id
- raw first-pass output
- raw verifier output when triggered
- parsed label
- uncertainty option index
- output schema version
- trigger category for verification
- unresolved/error category, if any; failures must not invent a label
- image load status
- seconds/sample
