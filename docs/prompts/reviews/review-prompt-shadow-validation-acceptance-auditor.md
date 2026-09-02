# Acceptance Auditor Review

Audit the Shadow Validation implementation against:

- `spec-4-shadow-private-validation-foundation.md`
- `epic-4-context.md`
- `_bmad-output/specs/spec-shadow-private-validation/SPEC.md`
- `_bmad-output/specs/spec-shadow-private-validation/dataset-contract.md`
- `_bmad-output/specs/spec-shadow-private-validation/evaluation-and-freeze-policy.md`

Implementation files are `src/multimodal_bias/validation.py`, `schemas.py`, `exceptions.py`, `cli.py`,
`configs/validation/`, `tests/test_shadow_validation.py`, and the Shadow assertions in
`tests/test_cli.py`. This workspace has no VCS baseline; treat those Shadow additions as the diff.

For every unmet acceptance criterion or violated boundary, report severity, exact file/line, governing
requirement, evidence, and minimal correction. Explicitly check that evaluation/test artifacts cannot
author the corpus, review separation is enforced, all freeze gates are fail-closed, frozen artifacts
detect later mutation, and sealed evaluation exports aggregates only.
