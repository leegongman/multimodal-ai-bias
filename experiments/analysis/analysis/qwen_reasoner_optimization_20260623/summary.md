# Qwen Reasoner Optimization Summary

Date: 2026-06-23

## Scope

This analysis is scoped to the current execution lock:

- Active model path: `Qwen/Qwen2.5-VL-7B-Instruct`.
- Active work: Qwen Reasoner v3 path for smoke, small A/B, runtime measurement, 8,500-row inference, parsing, and submission validation.
- Frozen work is not used for candidate design, execution, benchmarking, or repair.
- Existing shared/high-score Reasoner text is treated as a baseline design reference and is not modified.

The current directory did not present as a git repository to `git status`, so current-state evidence is based on direct file inspection.

## Evidence Sources

- `AGENTS.md`: confirms the active Qwen2.5-only lock and frozen scope.
- `configs/models/qwen2_5_vl_7b.yaml`: confirms the active local Qwen2.5 model profile.
- `configs/prompts/reasoner_v3.yaml`: current v3 schema prompt and output contract.
- `src/multimodal_bias/parsing.py`: strict v3 parser requiring `uncertainty_option_index`.
- `src/multimodal_bias/submission.py`: submission validation requires valid parsed rows and consistent uncertainty fields.
- `scripts/run_inference_14006_vllm.py`: shared Reasoner-style prompt and parser behavior used as the high-performing baseline reference.
- `data/raw/open/test/test.csv`: official 8,500-row test data structure.
- `data/raw/open/sample_submission.csv`: submission row structure.

## Main Finding

The best direction is not to replace the shared Reasoner philosophy. The best direction is to preserve its high-performing balance:

1. Use concrete stated facts and clearly visible evidence.
2. Treat one explicit stated action or fact as valid evidence.
3. Use opposite facts and elimination when the context supports them.
4. Choose uncertainty only when person identity or relevant evidence remains genuinely unresolved.
5. Never resolve ambiguity from stereotypes or protected/appearance attributes.

The Qwen2.5 v3 path should absorb only the parts that are structurally safer:

- Explicit option-index mapping.
- Explicit uncertainty-option index.
- Strict parseable output.
- A narrow guard against subjective visual over-inference.

## Candidate Set

Seven candidate directions are documented in `candidate_prompts.md`:

- Candidate A: Shared Minimal + Index Safety.
- Candidate B: Objective Visual Evidence Balanced.
- Candidate C: Conservative Hidden-Safe Likely/Protected.
- Candidate D: Explicit Evidence and Elimination Forward.
- Candidate E: Narrow Subjective Visual Guard.
- Candidate F: Compressed Qwen2.5 Instruction-Following.
- Candidate G: Parser-Stable v3 Contract First.

## Current Recommendation

Primary candidate for first real A/B: Candidate E.

Rationale:

- It changes the shared Reasoner least while addressing the most hidden-relevant risk: inferring ability, morality, emotion, career/family commitment, or social role from expression, posture, clothing, or protected attributes alone.
- It should preserve the shared Reasoner behavior on explicit facts and elimination.
- It avoids the over-unknown risk of a broad safety prompt.

Backup candidate: Candidate A.

Rationale:

- It is the closest to the shared Reasoner baseline while making label/index and uncertainty position explicit.
- If Candidate E regresses public-like behavior, Candidate A is the safest fallback.

## Completion Status

This folder contains:

- `data_profile.md`: 8,500-row data profile.
- `shared_reasoner_analysis.md`: shared Reasoner and v3 parser analysis.
- `candidate_prompts.md`: seven candidate prompts.
- `candidate_comparison.md`: risk/benefit comparison table.
- `validation_plan.md`: operational A/B and full-run gate plan.
- `final_recommendation.md`: current recommendation and adoption criteria.
- `prompt_yamls/reasoner_v3_candidate_{a..g}.yaml`: seven loadable v3 prompt templates for A/B.

Validation already run:

- `uv run python -c "... load_reasoner_prompt_template ..."` loaded all seven candidate YAML files as `reasoner_v3`.
