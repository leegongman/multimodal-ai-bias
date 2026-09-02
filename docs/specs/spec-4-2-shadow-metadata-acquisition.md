---
title: 'Acquire independent Shadow metadata and build the 1,200-record candidate pool'
type: 'feature'
created: '2026-06-21'
status: 'done'
baseline_commit: 'NO_VCS'
context:
  - 'epic-4-context.md'
  - 'docs/history/research/domain-shadow-validation-public-dataset-sources-research-2026-06-21.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Shadow Validation schema exists, but there is no independently sourced metadata pool from which licensed, person-rich images and relation examples can be selected. Manual downloads would lose source identity, hashes, and leakage controls.

**Approach:** Add a metadata-only acquisition command for pinned official Open Images/MIAP/VSR sources and a deterministic builder that emits exactly 900 MIAP/Open Images and 300 VSR candidate records. Execute both commands locally, preserving raw source bytes and a complete manifest; do not download image pixels or author final questions.

## Boundaries & Constraints

**Always:** Use only official allowlisted HTTPS sources declared in a versioned manifest; stream downloads through a partial file, hash bytes, capture URL/headers/time/size, and refuse overwrite; filter MIAP to 2–4 individually boxed people with objective geometry; strip perceived gender and age from every candidate/output; join Open Images attribution metadata; retain VSR source IDs/relations/captions only as authoring references; sample deterministically with seed `236722600`; emit ordered JSONL plus aggregate source/filter counts and hashes.

**Ask First:** Downloading any image pixels, accepting gated terms, changing source mix/counts, using a different dataset, or turning candidates into authored/reviewed Shadow records requires new human approval.

**Never:** Read any competition evaluation/test path or artifact; use predictions, disagreements, inferred answers, leaderboard behavior, or evaluation patterns; expose MIAP demographic attributes; treat VSR/Open Images annotations as final Shadow labels; silently skip malformed input; overwrite or mutate a completed acquisition; download the full image datasets.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Metadata acquisition | Pinned YAML manifest and new output directory | Raw metadata files plus deterministic manifest with source SHA-256 and response evidence | Partial download is removed; command exits non-zero without completed manifest |
| Candidate build | Complete acquisition manifest | Exactly 900 OI/MIAP + 300 VSR ordered metadata candidates and report | Reject hash mismatch, missing columns, malformed rows, insufficient eligible records, duplicate source IDs, or existing output |
| Sensitive MIAP columns | Gender/age fields exist in raw MIAP input | Fields are used neither for filtering nor output and are absent from candidate artifacts | Test fails if a sensitive key/value leaks |

</frozen-after-approval>

## Code Map

- `src/multimodal_bias/shadow_acquisition.py` -- strict source-manifest loading, streaming acquisition, verification, filtering, deterministic sampling, and artifact writing.
- `src/multimodal_bias/cli.py` -- expose metadata acquisition and candidate-pool commands with clean failures.
- `configs/validation/source-manifest-v1.yaml` -- pinned official metadata/annotation URLs and expected filenames.
- `tests/test_shadow_acquisition.py` and `tests/test_cli.py` -- local HTTP-free fixtures for download failure, hashing, no-clobber, filtering, sensitive-field exclusion, determinism, and CLI boundaries.
- `data/shadow-private/metadata-v1/` -- executed raw metadata and source manifest; no image pixels.
- `data/shadow-private/candidate-pool-v1/` -- executed 1,200-record candidate JSONL/report and hashes.

## Tasks & Acceptance

**Execution:**
- [x] Implement strict acquisition/source contracts and atomic, no-clobber streamed metadata downloads.
- [x] Implement fail-closed MIAP/Open Images and VSR parsing, attribution join, eligibility reporting, deterministic 900/300 selection, and sensitive-field exclusion.
- [x] Add CLI commands, pinned source manifest, and CPU/network-free tests.
- [x] Run the approved acquisition and pool builder, then verify counts, hashes, absence of pixel files, and absence of MIAP demographic fields in derived artifacts.

**Acceptance Criteria:**
- Given the pinned source manifest, when acquisition completes, then each raw metadata file is byte-bound to a source record and no image pixels were requested.
- Given valid source metadata, when the pool is built repeatedly with the same seed, then the ordered 1,200 candidate records are identical and contain complete attribution/reference fields but no final Shadow labels.
- Given malformed, changed, insufficient, duplicated, or sensitive-derived input, when either command runs, then it fails closed without a completed output artifact.

## Spec Change Log

## Design Notes

Raw MIAP inputs necessarily contain perceived demographic columns. They remain isolated in source metadata; derived candidates expose only neutral person-box geometry/count. VSR captions are retained for provenance and later independent rewriting, not copied into frozen questions.

## Verification

**Commands:**
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_shadow_acquisition.py tests/test_cli.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/multimodal_bias tests`
- `UV_CACHE_DIR=/tmp/uv-cache uv run multimodal-bias shadow-acquire-metadata --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run multimodal-bias shadow-build-candidate-pool --help`

**Results:** 51 focused tests passed. The complete suite passed 440 tests and retained three unrelated
scaffold failures because the pre-existing `models/snapshots/.gitkeep` placeholder is absent. The actual
candidate pool contains 1,200 rows and reproduces SHA-256
`87fb09e08238289d4420313fe35151fa9065a185c9a0ef5c727f1bc8fb7533ba`.

## Suggested Review Order

**Acquisition boundary**

- Streams allowlisted metadata atomically and records source evidence without pixels.
  [`shadow_acquisition.py:108`](src/multimodal_bias/shadow_acquisition.py#L108)

- Exposes explicit metadata-only and candidate-pool CLI operations.
  [`cli.py:584`](src/multimodal_bias/cli.py#L584)

**Candidate selection**

- Verifies source hashes and deterministically composes the 900/300 pool.
  [`shadow_acquisition.py:167`](src/multimodal_bias/shadow_acquisition.py#L167)

- Filters person geometry while isolating MIAP demographic fields.
  [`shadow_acquisition.py:290`](src/multimodal_bias/shadow_acquisition.py#L290)

- Restricts VSR to objective person relations with one record per image.
  [`shadow_acquisition.py:378`](src/multimodal_bias/shadow_acquisition.py#L378)

**Evidence and tests**

- Pins only official metadata endpoints and immutable VSR revision URLs.
  [`source-manifest-v1.yaml:1`](configs/validation/source-manifest-v1.yaml#L1)

- Covers no-clobber, cleanup, determinism, sensitive exclusion, geometry, and mutation.
  [`test_shadow_acquisition.py:163`](tests/test_shadow_acquisition.py#L163)
