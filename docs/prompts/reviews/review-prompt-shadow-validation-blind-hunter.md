# Blind Hunter Review

Review only the implementation change described below. Do not use the spec or project context.
Report concrete defects with severity, file, line, and failure scenario; do not report style preferences.

## Change under review

- New strict Shadow record/audit/freeze/evaluation implementation in `src/multimodal_bias/validation.py`.
- New Shadow immutable contracts appended to `src/multimodal_bias/schemas.py`.
- New `ShadowValidationError` in `src/multimodal_bias/exceptions.py`.
- New `shadow-audit`, `shadow-freeze`, and `shadow-evaluate` commands in `src/multimodal_bias/cli.py`.
- New human author/reviewer templates under `configs/validation/`.
- New coverage in `tests/test_shadow_validation.py` and CLI help assertion in `tests/test_cli.py`.

Read those changed files as the complete best-effort diff (this workspace has no VCS baseline).
Focus on corruption, incorrect metrics, validation bypasses, unsafe writes, and data leakage.
