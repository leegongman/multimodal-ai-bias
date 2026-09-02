---
title: 'Build the verified Shadow image pool and 600 pending review records'
type: 'feature'
created: '2026-06-21'
status: 'done'
baseline_commit: 'NO_VCS'
context:
  - 'epic-4-context.md'
  - 'docs/history/research/domain-shadow-validation-public-dataset-sources-research-2026-06-21.md'
---

<frozen-after-approval reason="human-owned intent — explicitly authorized by the user's instruction to proceed">

## Intent

**Problem:** The 1,200-row metadata pool had no locally decodable pixels or competition-shaped records.

**Approach:** Verify individual Open Images attribution pages, original MD5 values, decode and duplicate
status; retain 600 images; generate exactly 600 balanced records that remain pending independent review.

## Boundaries & Constraints

**Always:** Preserve creator/title/landing/license evidence, image hashes and dimensions; reject missing
license evidence, MD5 mismatch, decode failure, small images, exact duplicates and dHash duplicates;
balance labels and uncertainty positions 200/200/200, selection/holdout 420/180 and all eight subsets.

**Ask First:** Human review and freeze remain separate actions.

**Never:** Claim these AI-authored candidates are human-authored, reviewed, frozen or promotion-ready;
use evaluation/test data; expose MIAP perceived demographic fields; use VSR pixels without per-image rights.

</frozen-after-approval>

## Code Map

- `src/multimodal_bias/shadow_acquisition.py` -- license/page/MD5/decode/duplicate image gates and balanced pending generation.
- `src/multimodal_bias/validation.py` -- full Pillow decode verification for Shadow images.
- `src/multimodal_bias/cli.py` -- `shadow-download-images` and `shadow-generate-pending` commands.
- `tests/test_shadow_acquisition.py` -- image and pending-corpus contract coverage.
- `data/shadow-private/image-pool-v1/` -- 600 verified but human-review-pending images and provenance.
- `data/shadow-private/pending-v1/` -- 600 balanced pending records and audit.

## Tasks & Acceptance

**Execution:**
- [x] Download exactly 600 source images through license-page, MD5, decode, size and duplicate gates.
- [x] Generate 600 balanced records with immutable image hashes and pending review status.
- [x] Audit the real corpus and verify that independent review is the sole remaining promotion violation.
- [x] Add deterministic, network-free tests and Pillow decode coverage.

**Acceptance Criteria:**
- Given 900 attributed candidates, when the image gate runs, then 600 unique decodable images and a
  rejection history are produced without VSR or sensitive MIAP data.
- Given the verified image pool, when pending generation runs, then all count/balance gates pass while
  promotion remains false solely because reviewed count is zero.

## Spec Change Log

## Verification

- 600 image files; 1,276,683,777 total image bytes; 183 rejected attempts.
- 600 records; labels and uncertainty positions each 200/200/200; 420 selection and 180 holdout.
- Audit violation: `all frozen records must be reviewed or adjudicated` only.
- 54 focused tests pass; targeted Ruff checks pass.

## Suggested Review Order

- Review network, rights, pixel-integrity and duplicate gates.
  [`shadow_acquisition.py:248`](src/multimodal_bias/shadow_acquisition.py#L248)

- Review deterministic 600-row balance and pending-only status.
  [`shadow_acquisition.py:369`](src/multimodal_bias/shadow_acquisition.py#L369)

- Review real decode enforcement at the freeze boundary.
  [`validation.py:429`](src/multimodal_bias/validation.py#L429)

- Review actual balance and the sole remaining audit violation.
  [`audit.json:1`](data/shadow-private/pending-v1/audit.json#L1)
