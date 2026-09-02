# Story 2.7 Blind Hunter Review Prompt

Use `bmad-review-adversarial-general`.

Review only the current contents of the following implementation and test files. Do not read the Story, SPEC, planning documents, or prior conversation. Treat this as a context-blind defect hunt. Report only concrete defects with severity, exact file/line evidence, impact, and minimal correction.

- `configs/prompts/reasoner_v3.yaml`
- `src/multimodal_bias/cli.py`
- `src/multimodal_bias/models/dummy.py`
- `src/multimodal_bias/parsing.py`
- `src/multimodal_bias/prompting/guards.py`
- `src/multimodal_bias/prompting/templates.py`
- `src/multimodal_bias/schemas.py`
- `src/multimodal_bias/submission.py`
- `tests/test_cli.py`
- `tests/test_model_adapter.py`
- `tests/test_parsing.py`
- `tests/test_prompting.py`
- `tests/test_reasoner.py`
- `tests/test_reasoner_v3_contract.py`
- `tests/test_submission.py`

Focus on runtime correctness, fail-open behavior, schema/version mixing, type confusion, malformed input handling, compatibility regressions, and tests that pass without proving their stated behavior.
