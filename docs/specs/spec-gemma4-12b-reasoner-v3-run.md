---
title: 'Run Gemma 4 12B with Reasoner v3 on RTX A6000'
type: 'feature'
created: '2026-06-20'
status: 'in-progress'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Qwen3.5-9B with Reasoner v3 produced a valid Public baseline of 0.94 but required 96 minutes 55 seconds and one output hit the 256-token cap. The next controlled experiment must change only the model to Gemma 4 12B while preventing a single truncated output from invalidating the full run.

**Approach:** Add an isolated Gemma 4 12B vLLM runner that preserves the v3 prompt, parser, label semantics, deterministic decoding, and artifacts. Use a compact bounded evidence string, start each sample at 256 output tokens, and retry only incomplete or invalid rows once at 512 tokens before publishing a submission.

## Boundaries & Constraints

**Always:** Use only the official gated `google/gemma-4-12B-it` checkpoint at a recorded revision; keep the existing Qwen environment, model snapshot, runs, and code intact; create an isolated Gemma runtime; disable thinking; retain all seven v3 output fields and nine valid semantic combinations; preserve both first-attempt and retry evidence; validate all 8,500 official IDs in order before producing `submission.csv`.

**Ask First:** The user must accept the Gemma license and authenticate Hugging Face on RunPod if the gated checkpoint cannot be downloaded. Halt if BF16 cannot fit the A6000 without CPU/disk offload; do not silently switch to an unofficial quantization.

**Never:** Modify or delete the Qwen baseline artifacts, manually infer a failed label, replace an invalid row with a fallback, enable a verifier, change Reasoner v3 decision rules, touch other frozen models or Epics, or start the 8,500-row run before real-image and measured-subset gates pass.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Normal row | Valid JSON completes within 256 tokens | Preserve first attempt and parse once | No retry |
| Truncated or invalid row | First attempt fails v3 parse or ends at token cap | Retry same sample once with 512 tokens | Fail row if retry is still invalid |
| Full run | All 8,500 rows valid after selective retries | Emit immutable raw, parsed, prediction, summary, and submission artifacts | Publish no submission if any row remains invalid |
| Runtime incompatibility | Current vLLM/Transformers lacks Gemma 4 Unified | Use a separate compatible environment | Preserve Qwen environment unchanged |

</frozen-after-approval>

## Code Map

- `scripts/run_gemma4_12b_v3_vllm.py` -- isolated OpenAI-compatible Gemma inference, bounded output, selective retry, and artifact publication.
- `scripts/run_qwen35_v3_vllm.py` -- proven v3 schema, normalization, concurrency, telemetry, and artifact pattern to reuse without changing its model behavior.
- `configs/prompts/reasoner_v3.yaml` -- immutable decision prompt and seven-field output contract.
- `tests/test_gemma4_v3_runner.py` -- CPU-safe tests for model isolation, semantic schema, retry selection, and fail-closed publication.

## Tasks & Acceptance

**Execution:**
- [ ] `scripts/run_gemma4_12b_v3_vllm.py` -- implement the official model identity, compact semantic schema, first-attempt/retry audit records, selective 256→512 retry, and no-clobber full-run outputs.
- [ ] `tests/test_gemma4_v3_runner.py` -- prove valid rows are not retried, capped/invalid rows retry once, retry failure blocks submission, and official ordering is preserved.
- [ ] RunPod isolated Gemma environment -- install a compatible vLLM/Transformers stack, download the gated official snapshot, and verify offline loading without altering the Qwen environment.
- [ ] RunPod execution -- pass server health, real-image output, fixed subset reliability/runtime, then run all 8,500 rows and validate the submission artifact.

**Acceptance Criteria:**
- Given the official Gemma snapshot and unchanged v3 prompt, when deterministic non-thinking inference runs, then every accepted row satisfies the existing parser and records model revision, prompt/image hashes, token counts, attempt number, and GPU timing.
- Given a first attempt that is capped or invalid, when selective retry runs, then only that sample is regenerated at 512 tokens and no label is synthesized outside model output.
- Given a completed full run, when artifacts publish, then exactly 8,500 ordered rows are valid and `submission.csv` has exactly 8,501 lines.

## Spec Change Log

## Design Notes

The 512-token budget is a recovery path, not the default. Bounding `evidence` in the guided JSON schema prevents the model from using that field as an unbounded reasoning channel while preserving its required non-empty audit evidence. The retry record remains separate from the selected final record so truncation frequency and cost are measurable.

## Verification

**Commands:**
- `uv run ruff check scripts/run_gemma4_12b_v3_vllm.py tests/test_gemma4_v3_runner.py` -- expected: no findings.
- `uv run pytest -q tests/test_gemma4_v3_runner.py tests/test_reasoner_v3_contract.py tests/test_submission.py` -- expected: all tests pass.
- RunPod fixed subset -- expected: zero final parse failures and explicit retry count before full authorization.
- RunPod full validation -- expected: 8,500 valid rows, 8,501 submission lines, immutable hashes, and recorded elapsed time.
