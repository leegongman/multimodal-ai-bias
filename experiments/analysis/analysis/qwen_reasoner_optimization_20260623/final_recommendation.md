# Final Recommendation Before A/B

## Recommended First Candidate

Candidate E: Narrow Subjective Visual Guard.

## Why Candidate E

Candidate E is the best first challenger because it preserves the shared Reasoner's core behavior while adding one general hidden-safe improvement.

It keeps:

- Decisive use of explicit context facts.
- Single-instance evidence.
- Direct inference from stated facts.
- Opposite-property and elimination reasoning.
- Uncertainty for genuinely unresolved references.

It adds:

- Explicit label/index safety.
- Explicit uncertainty-option mapping.
- Objective-vs-subjective image evidence distinction.
- A narrow rule against inferring traits from expression, posture, clothing, body language, protected attributes, or appearance alone.

This is the smallest change that targets the largest hidden-relevant failure mode without turning the Reasoner into an over-cautious uncertainty selector.

## Backup Candidate

Candidate A: Shared Minimal + Index Safety.

Use Candidate A if Candidate E shows:

- Over-unknown regressions on explicit stated facts.
- Failure to use objective image evidence.
- Excessive disagreement with the shared baseline.

Candidate A is the safest v3-compatible baseline because it changes the shared Reasoner least.

## Candidates Not Recommended as Final Yet

Candidate C:

- Too conservative.
- Likely to regress public-like rows where a single stated action is intentionally enough.

Candidate D:

- Useful stress test for public preservation.
- Riskier for hidden because it may over-apply single-instance reasoning to tendency questions.

Candidate G:

- Strong for parser stability.
- May repeat current v3's schema-first weakness.

Candidate F:

- Good if instruction following is poor.
- Too compressed to be first-choice for nuanced reasoning.

Candidate B:

- Valuable if A/E under-use image evidence.
- Needs careful disagreement review because "objective visual" can drift into subjective inference.

## Rules Not To Add

Do not add these:

- `All likely questions should be uncertainty.`
- `All protected-attribute questions should be uncertainty.`
- `Expression/posture/clothing can determine personality, ability, morality, emotion, or commitment.`
- `Expression/posture/clothing can never be evidence.`
- `A single stated action is never enough.`
- `A single stated action always proves a broad tendency.`
- `Unknown is usually label 2.`
- `Prefer the answer that seems socially fair regardless of option text.`
- Any rule that names a specific public row, exact repeated question, or inferred public answer.

## Current Implementation State

Seven non-destructive candidate YAML files have been created under:

- `experiments/analysis/qwen_reasoner_optimization_20260623/prompt_yamls/`

All seven load successfully through `load_reasoner_prompt_template` as `reasoner_v3`.

## Next Implementation Step

Run only the active Qwen2.5 path through:

1. Real-image smoke.
2. Stratified small A/B against the current v3/shared-style baseline.
3. Disagreement analysis.
4. Full 8,500 inference only after gates pass.

Do not replace `configs/prompts/reasoner_v3.yaml` until Candidate E passes the adoption gate.
