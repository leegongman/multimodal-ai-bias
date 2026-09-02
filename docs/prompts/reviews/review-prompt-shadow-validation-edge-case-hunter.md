# Edge Case Hunter Review

Inspect the project and walk every branching path and boundary in these changed files:

- `src/multimodal_bias/validation.py`
- `src/multimodal_bias/schemas.py`
- `src/multimodal_bias/exceptions.py`
- `src/multimodal_bias/cli.py`
- `configs/validation/`
- `tests/test_shadow_validation.py`

The workspace has no VCS baseline, so treat the listed Shadow additions as the change. Report only
unhandled edge cases with severity, exact file/line, reproducible input, observed result, and expected
result. Emphasize path traversal, malformed JSON/types, empty splits, duplicate semantics, image
integrity, hash mutation, no-clobber behavior, divide-by-zero, metrics correctness, and sealed leakage.
