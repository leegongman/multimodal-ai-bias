# Validation Plan

This plan is designed for one final submission, but several candidate prompts can be tested before selecting that single submission.

## Constraints

- Use only the active Qwen2.5 path.
- Do not run, benchmark, repair, or use frozen non-Qwen candidates.
- Do not modify existing shared/high-score artifacts.
- Do not create row-specific answer patches.
- Do not infer correctness from public test rows alone. Use disagreement shape, parser validity, and hidden-safe reasoning as selection evidence.

## Phase 0: Static Validation

For each candidate prompt:

- Confirm it preserves explicit option-index mapping.
- Confirm it identifies uncertainty option position.
- Confirm final output is v3-compatible.
- Confirm it keeps the shared Reasoner's single-instance evidence rule.
- Confirm it does not add row-specific patterns.
- Confirm it does not hard-code any uncertainty label.

Reject immediately if:

- It implies label `2` means unknown.
- It says all `likely` questions should be uncertainty.
- It forbids objective image evidence.
- It permits protected attributes as trait evidence.
- It changes model scope away from Qwen2.5.

## Phase 1: Real-Image Smoke Set

Build a small smoke set of 12-18 rows from `test.csv` by strata, not by desired answer:

- uncertainty option index 0/1/2: at least 3 rows each.
- explicit stated action: at least 3 rows.
- negative or elimination: at least 3 rows.
- objective image identity/action: at least 3 rows.
- likely + protected attribute: at least 3 rows.
- subjective visual over-inference risk: at least 2 rows.

Gate:

- All rows produce parse-valid v3 JSON.
- No missing or duplicate sample IDs.
- No invalid label or uncertainty index.
- Evidence type is consistent with selected label.
- No obvious prompt-format drift.

## Phase 2: Stratified Small A/B

Run baseline and candidate prompts on the same deterministic Qwen2.5 settings.

Suggested size: 150-300 rows.

Strata:

- 30 likely + protected.
- 30 explicit single-instance stated fact.
- 30 elimination/opposite/negative.
- 30 objective visual identity/action.
- 20 subjective visual risk.
- 20 health/abuse/crime/morality.
- 20 education/STEM/ability.
- balanced uncertainty index positions.

Analyze:

- Disagreement count by stratum.
- Candidate changes from uncertainty to person.
- Candidate changes from person to uncertainty.
- Evidence type changes.
- Protected risk flag changes.
- Parse failures.
- JSON schema failures.

Manual review sample:

- All disagreements in subjective visual risk.
- All disagreements where candidate chooses a protected person and baseline chooses uncertainty.
- All disagreements where candidate chooses uncertainty and baseline chooses a person from explicit stated fact.
- Random 20 agreements to check shared failure modes.

Gate:

- Parse validity: 100%.
- No row-order or schema issue.
- No broad over-unknown pattern on explicit stated facts.
- No broad over-person pattern on likely/protected ambiguous rows.
- Candidate E/A must preserve baseline decisions unless a general rule explains the change.

## Phase 3: Larger A/B

Suggested size: 800-1,200 rows if runtime permits.

Sampling:

- Preserve uncertainty index balance.
- Preserve major domain proportions.
- Oversample high-risk domains enough for signal:
  - likely/protected.
  - education/STEM/ability.
  - morality/crime/safety.
  - work/family commitment.
  - subjective visual risk.

Gate:

- Parse validity: 100%.
- Runtime projection fits the submission window.
- Disagreement rate is not excessive.
- Candidate has fewer manually judged unsafe stereotypes without causing many explicit-fact regressions.

## Phase 4: Full 8,500 Inference

Before full run:

- Freeze candidate prompt hash.
- Record model config and decoding settings.
- Record data hashes.
- Confirm output directory is new.
- Confirm image paths resolve.

After full run:

- Validate raw output count: 8,500.
- Validate parsed count: 8,500.
- Validate parse_status all valid.
- Validate labels all in `0/1/2`.
- Validate uncertainty indexes all in `0/1/2`.
- Validate `uncertainty_signal` consistency.
- Validate CSV row order exactly matches sample submission.
- Validate no duplicate/missing sample IDs.
- Validate submission CSV has exactly expected columns.

## Disagreement Decision Rules

Prefer a candidate over baseline only if disagreements are explainable by generalizable rules:

- Good change: candidate uses explicit stated fact that baseline ignored.
- Good change: candidate uses objective image action/identity that baseline ignored.
- Good change: candidate rejects stereotype/appearance inference that baseline used.
- Good change: candidate handles negative/opposite elimination more consistently.

Bad change:

- Candidate chooses uncertainty despite explicit stated fact.
- Candidate chooses a person from protected attribute or appearance only.
- Candidate treats expression/posture/clothing as evidence of ability, morality, commitment, or tendency.
- Candidate ignores option text and appears to assume a fixed label meaning.
- Candidate increases invalid or fallback parsing.

## Final Adoption Gate

A candidate can become the final submission Reasoner only if:

- It passes all parser and CSV gates.
- It is deterministic under the chosen decoding settings.
- It preserves shared Reasoner strengths on explicit facts and elimination.
- It improves or plausibly reduces hidden risk on subjective visual/protected ambiguity.
- It does not require row-specific patches.
- It has a clear fallback candidate if full-run disagreement looks unsafe.

