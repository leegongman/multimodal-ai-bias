# Qwen3.5 Targeted Repair Review

Use `bmad-review-adversarial-general` in a fresh session.

Review these changed files with no conversation context:

- `scripts/run_qwen35_v3_vllm.py`
- `scripts/merge_qwen35_v3_repair.py`

Focus on whether the implementation:

- selects exactly one official sample when `--sample-id` is supplied;
- keeps `--sample-id` mutually exclusive with `--limit`;
- rejects any source run that is not exactly 8,500 official ordered rows;
- accepts only a one-row, valid repair run for the named invalid sample;
- preserves all source and repair artifacts byte-for-byte;
- reparses every merged output and refuses to publish if any row remains invalid;
- publishes only to a new no-clobber directory;
- emits an exact `sample_id,label` submission with 8,500 ordered rows;
- records sufficient provenance and hashes to audit the replacement;
- cannot silently insert a fallback or manually inferred label.

Return at least ten precise findings. Do not modify files.
