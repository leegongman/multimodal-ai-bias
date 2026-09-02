---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'domain'
research_topic: 'Shadow Validation public dataset sources'
research_goals: 'Select licensed, independent image and multimodal reasoning sources for a 600-record evaluation corpus without using competition test data'
user_name: 'gongman'
date: '2026-06-21'
web_research_enabled: true
source_verification: true
---

# Research Report: domain

**Date:** 2026-06-21
**Author:** gongman
**Research Type:** domain

---

## Research Overview

This research defines a legally auditable, evaluation-independent source strategy for a 600-record
Shadow Validation corpus. It verifies task fit, access methods, competition rules, image-license duties,
MIAP acceptable-use limits, and a deterministic authoring/review pipeline using current official sources.

The recommended corpus is 360 public-source records, 150 independently authored records, and 90
synthetic candidates, split into 420 selection and 180 sealed-holdout records. Open Images/MIAP supplies
person-rich natural scenes and VSR supplies controlled relation reasoning. All records remain pending
until a different human independently reviews the answer and evidence. See the Research Synthesis below
for the final decision and execution sequence.

## Domain Research Scope Confirmation

**Research Topic:** Shadow Validation public dataset sources
**Research Goals:** Select licensed, independent image and multimodal reasoning sources for a
600-record evaluation corpus without using competition test data.

**Confirmed corpus plan:**

- 360 public-source records, 150 independently authored counterexamples, 90 synthetic candidates
- 420 selection records and 180 sealed-holdout records
- Eight required reasoning subsets with position and ambiguity balance
- No use of official test records, predictions, disagreements, or leaderboard feedback
- All generated records remain pending until independent human review

**Research Methodology:**

- Verify dataset ownership, license, access conditions, image availability, and task fit
- Prefer authoritative dataset cards, official repositories, papers, and license files
- Do not download data or accept gated terms during research

**Scope Confirmed:** 2026-06-21

---

<!-- Content will be appended sequentially through research workflow steps -->

## Dataset Ecosystem Analysis

### Primary image pool: Open Images

Open Images is the strongest primary candidate because it provides natural photographs, human-verified
labels, person/object bounding boxes, and visual relationships. Its official repository describes about
9 million image URLs; annotations are CC BY 4.0 and repository contents Apache 2.0. Images are listed as
CC BY 2.0, but the publisher explicitly warns that each selected image's license must be verified.

- Proposed allocation: 240 of the 360 public-source records
- Best fit: visual grounding, role/function, elimination, stereotype trap, expression trap
- Required control: retain creator, source URL, license URL, image ID, retrieval date, and local hash
- Risk: dataset-level license metadata is not sufficient proof for an individual Flickr image

Sources: [official Open Images repository](https://github.com/openimages/dataset/blob/main/READMEV3.md),
[Open Images V4 paper](https://arxiv.org/abs/1811.00982)

### Person-balanced sampling aid: Open Images Extended MIAP

MIAP contains 100,000 Open Images V6 images with manually annotated visible-person boxes. Its official
data card states that annotations are CC BY 4.0, access is open, images are obtained separately, and
users must read the perceived-gender and perceived-age acceptable-use notes. These perceived attributes
must never be used as answer evidence; they are useful only for auditing coverage and stereotype traps.

- Proposed allocation: MIAP indexes 120 of the 240 Open Images records; it is not an additional image pool
- Best fit: scenes with multiple visible people and counterexamples against appearance-based selection
- Required control: never expose perceived demographic annotations to the Reasoner prompt or use them as labels
- Risk: demographic annotation imbalance and the ethical risk of treating perceived attributes as truth

Source: [official MIAP data card](https://storage.googleapis.com/openimages/open_images_extended_miap/Open%20Images%20Extended%20-%20MIAP%20-%20Data%20Card.pdf)

### Controlled relation pool: Visual Spatial Reasoning

VSR contains 10,972 validated natural image-text pairs covering 66 spatial relations. The official
repository uses Apache 2.0 for its code/data metadata and requires images to be downloaded separately.
The benchmark reports a human ceiling above 95% and highlights orientation and reference-frame failures,
which makes it useful for objective grounding rather than subjective person inference.

- Proposed allocation: 120 of the 360 public-source records
- Best fit: visual grounding, elimination, disambiguated text, parsing stress
- Required control: verify and retain the underlying image license separately
- Risk: true/false captions require independent conversion into the three-choice person/uncertainty contract

Sources: [official VSR repository](https://github.com/cambridgeltl/visual-spatial-reasoning),
[VSR paper](https://arxiv.org/abs/2205.00363)

### Excluded as a primary source: Visual Genome

Visual Genome is highly relevant technically, with 108,077 images and dense region, object, relationship,
and VQA annotations. However, search results expose conflicting third-party license declarations, while
the current official site does not present a sufficiently clear image-level license trail. It should not
be incorporated until the original image provenance and license can be verified per selected item.

Source: [Visual Genome project](https://visualgenome.org/)

### Ecosystem conclusion

The most defensible public-source mix is Open Images/MIAP plus VSR, not a broad scrape of multiple VQA
benchmarks. Open Images supplies diverse multi-person natural scenes; MIAP improves person-box coverage;
VSR supplies controlled relation reasoning. The main bottleneck is not availability but per-image
license verification, independent conversion to the competition-like contract, and human label review.

**Confidence:** high for dataset/task fit; medium for final image availability until individual URLs and
licenses are checked. No dataset or image has been downloaded during this research step.

## Source Comparison and Acquisition Design

### Ranked source decision

| Rank | Source | Role | Advantages | Blocking risk |
|---:|---|---|---|---|
| 1 | Open Images V6/V7 | 240 public records | Direct image-ID downloader, person boxes, relationships, author/license metadata | Individual Flickr license must be rechecked |
| 2 | MIAP | Person-rich index over Open Images | 100k person-focused images, manual person boxes, fairness documentation | Perceived attributes require strict acceptable-use isolation |
| 3 | VSR | 120 relation records | Validated relations and controlled failure types | Underlying COCO image rights are separate from Apache dataset metadata |
| excluded | Visual Genome | none in v1 | Dense relationships and VQA | Original image-level license trail is not clear enough |

Open Images is operationally dominant: its official download page supports downloading exact image IDs
instead of the complete corpus and publishes image metadata containing original URL, landing page,
license, author, title, original checksum, and rotation. It also distinguishes human-verified labels
from machine-generated labels. This enables a small, auditable 240-image acquisition rather than a
large blind download.

Source: [Open Images V6 official download documentation](https://storage.googleapis.com/openimages/web/download_v6.html)

### Proposed acquisition funnel

The 600 final records should not be generated directly from 600 first-pass images. The public branch
needs an oversampled funnel so that dead URLs, license failures, weak evidence, duplicates, and human
review rejection do not destroy coverage.

1. Filter metadata to approximately 900 Open Images IDs with at least two non-group person boxes.
2. Use MIAP only as an index for 450 of those IDs; do not import perceived attributes into questions.
3. Filter approximately 300 VSR rows for person-object/person-person spatial relations.
4. Verify individual landing page, license, author, and source availability before pixel download.
5. Download at most 600 public candidates; retain only 360 after objective-evidence review.
6. Produce 150 independently authored counterfactual records from separately owned/permitted images.
7. Produce 90 synthetic candidates, which remain pending until human review.

The oversampling target is deliberately larger than 360 because URL attrition and annotation rejection
are expected. Reusing one image for multiple near-duplicate questions is disallowed in the frozen set.

### Exact 600-record reasoning allocation

Subset tags may overlap, but each record receives one primary stratum for reporting and sampling.

| Primary stratum | Count | Main source |
|---|---:|---|
| ambiguous | 120 | Open Images, independent authoring, synthetic |
| disambiguated_text | 90 | Open Images counterfactual pairs |
| visual_grounded | 90 | Open Images/MIAP and VSR |
| elimination | 75 | Open Images relationships and VSR |
| stereotype_trap | 75 | MIAP-indexed scenes with independently written neutral evidence |
| expression_trap | 60 | Open Images scenes; expression never supplies the correct label |
| role_or_function | 60 | Open Images human-action/relationship annotations |
| parsing_stress | 30 | All sources with controlled option phrasing |
| **Total** | **600** | 360 public, 150 independent, 90 synthetic |

Uncertainty-option positions are exactly 200/200/200. Expected labels are also balanced 200/200/200.
The split is 420 selection and 180 sealed holdout. Source, primary stratum, position, expected label,
and split assignment must be stratified together with a recorded seed before questions are authored.

### Quality and leakage barriers

- Official competition test rows, images, predictions, disagreements, and leaderboard movement are never inputs.
- Existing source labels may propose candidates but cannot become final labels without independent review.
- Public-source images keep attribution and license evidence beside the local SHA-256.
- MIAP perceived demographic fields are stored in a restricted audit table, not the record or prompt.
- VSR text is not copied verbatim; the visual relation is independently rewritten into the target contract.
- Synthetic candidates and author-written answers remain pending until a different human reviews them.
- Sealed-holdout sample contents are hidden after freeze; only aggregate metrics are exported.

### Download decision

The next executable step would download only metadata and annotations first, not image pixels. Metadata
is sufficient to create the auditable candidate-ID pool and estimate how many original landing pages
still expose valid license information. Pixel download should occur only after that audit succeeds.

**Confidence:** high for the Open Images workflow; medium for VSR until underlying COCO/Flickr image
license evidence is verified per selected item. No data has been downloaded.

## Rules, Licensing, and Privacy Requirements

### Competition rules

The competition explicitly permits public data, self-collected data, synthetic data, and generative-AI
data within legal constraints. It also requires compliance with copyright, license, privacy, and data-use
terms. The decisive leakage boundary is equally explicit: evaluation data cannot be used to generate or
reconstruct similar questions, passages, choices, training data, prompts, or rules, and inferred
evaluation answers cannot be used.

This validates an independently sourced Shadow suite but prohibits using the 8,500 evaluation rows,
their question-type distribution, prediction disagreements, or leaderboard response as authoring input.
The research and acquisition scripts must therefore operate without reading `data/raw/open/test`.

Source: [official Multimodal competition rules](공식 원문 링크 제외)

### CC BY image obligations

CC BY 2.0 and 4.0 permit sharing and adaptation, including commercial use, when attribution is provided.
The record manifest must retain creator/attribution party, title when supplied, original landing URL,
license URL, and modification notice. CC also warns that copyright permission does not necessarily clear
publicity, privacy, or moral rights.

Operationally, a row is rejected when the original landing page is unavailable, license metadata is
missing or inconsistent, the creator cannot be attributed, or the image creates an avoidable privacy or
dignity concern. Private storage does not eliminate the need for provenance evidence.

Sources: [CC BY 2.0 deed](https://creativecommons.org/licenses/by/2.0/),
[CC BY 4.0 deed](https://creativecommons.org/licenses/by/4.0/)

### MIAP acceptable-use boundary

MIAP's official data card classifies use as conditional. It identifies person detection and fairness
evaluation as safe uses, and explicitly identifies gender or age classification as unsafe. It also states
that perceived age is not actual age and that perceived gender presentation cannot establish gender
identity. The attributes are imbalanced and culturally contingent.

Therefore:

- MIAP may select images with multiple person boxes.
- Person boxes may support neutral left/right or object-interaction references.
- Perceived gender/age columns may be used only in a restricted coverage audit.
- Those columns cannot create labels, context, questions, answers, or model prompts.
- No output may claim a person's actual age, gender, ethnicity, occupation, intent, or emotion from appearance.

Source: [official MIAP data card](https://storage.googleapis.com/openimages/open_images_extended_miap/Open%20Images%20Extended%20-%20MIAP%20-%20Data%20Card.pdf)

### VSR and underlying image rights

Apache 2.0 on the VSR repository covers the released project materials; its own instructions say image
files are downloaded separately. Consequently, repository licensing cannot be treated as clearance for
the underlying COCO/Flickr pixels. Each selected VSR image must pass the same image-level attribution and
rights audit as Open Images, or be excluded.

Source: [official VSR repository](https://github.com/cambridgeltl/visual-spatial-reasoning)

### Compliance artifact requirements

Each public candidate must preserve:

- dataset/source name and immutable source record ID
- original image landing URL and pixel URL
- creator, title, license identifier and canonical license URL
- retrieval date, original checksum when supplied, downloaded SHA-256 and local path
- modification/rotation/crop status
- author ID, independent reviewer ID, review decision and evidence note
- confirmation that no competition evaluation artifact was used

The attribution manifest remains with every freeze. Removing an image after a later rights request creates
a new dataset version; the old freeze cannot be silently altered.

### Risk decision

| Risk | Decision |
|---|---|
| Test-derived leakage | Hard block before authoring or freeze |
| Missing or unverifiable image license | Reject image |
| Missing attribution fields | Reject image |
| MIAP attribute used as identity/answer evidence | Hard block |
| Face-centric or humiliating context | Reject image |
| Dead original URL after download | Preserve retrieval evidence; require review before freeze |
| Synthetic author self-review | Hard block |
| Sample-level sealed output | Hard block |

This is a competition compliance design, not legal advice. Any disputed image is cheaper to replace than
to rationalize. No metadata or pixels have been downloaded.

## Technical Acquisition and Authoring Plan

### Minimal acquisition stack

The implementation should avoid downloading an entire dataset or introducing the heavy FiftyOne runtime
unless manual exploration becomes necessary. Open Images officially supports both exact-ID downloads via
its downloader and exact `image_ids` through FiftyOne. VSR metadata is a small JSON corpus and exposes
COCO image URLs separately.

Recommended stack:

- Python 3.10 standard library for streamed CSV/JSON parsing, URL retrieval, hashes, and manifests
- official Open Images `downloader.py` for approved exact image IDs
- Pillow only for full decode verification, dimensions, rotation, thumbnail generation, and dHash
- deterministic seed `236722600` for sampling, option placement, label placement, and split assignment
- existing Shadow schema/audit/freeze commands as the only route to promotion-ready artifacts

Sources: [Open Images official downloader](https://github.com/openimages/dataset),
[Open Images exact-ID documentation](https://storage.googleapis.com/openimages/web/download_v6.html),
[FiftyOne Open Images integration](https://docs.voxel51.com/integrations/open_images.html),
[official VSR dataset card](https://huggingface.co/datasets/cambridgeltl/vsr_random)

### Staged artifact pipeline

1. `source-metadata/` — pinned source URLs, retrieval timestamps, response hashes, licenses.
2. `candidate-pool.jsonl` — metadata-only candidate IDs and objective annotations; no questions.
3. `license-audit.jsonl` — individual pass/reject decision and attribution evidence.
4. `images/` — only approved pixels, named by SHA-256; originals remain unchanged.
5. `authoring-queue.jsonl` — deterministic primary stratum, label position, split, and author assignment.
6. `pending-records.jsonl` — 600 authored candidates with no reviewed status.
7. `review-decisions.jsonl` — independent decisions, evidence, rejection and adjudication history.
8. `reviewed-records.jsonl` — only approved rows, assembled without overwriting pending history.
9. `frozen-v1/` — immutable 600-row corpus generated by `shadow-freeze`.

Every stage is no-clobber and content-addressed. A failure cannot silently skip into the next stage.

### Candidate filtering

Public-image filters operate only on independent source annotations:

- two to four individually boxed people, excluding group boxes
- minimum person-box area and image dimensions sufficient for A6000 inference
- no extreme occlusion/truncation for resolvable questions
- allow occlusion deliberately for ambiguous questions, but only after review
- objective person-object or person-person relations preferred
- reject watermarks, collages, explicit content, minors in sensitive contexts, humiliation, medical scenes,
  identity claims, or images whose fair use depends on inference rather than a documented license
- SHA-256 exact duplicate removal followed by dHash near-duplicate review

The filter intentionally does not inspect the competition evaluation dataset or tune source frequencies
to match leaderboard behavior.

### Authoring design

Each approved image receives one primary question only. Public source captions and VSR text are evidence
for candidate selection, not text to copy. The author writes a new context and question under one of
three evidence modes:

- `text-resolvable`: context uniquely identifies person A or B through an explicit neutral fact.
- `visual-resolvable`: an objective position, object, or action identifies person A or B.
- `insufficient`: neither text nor objective image evidence uniquely identifies either person.

Counterfactual pairs share a source scene but not a frozen image record: one authoring version may add a
neutral disambiguating fact and another may remove it. Only one member enters sealed holdout; linked
counterfactuals cannot cross selection/holdout in a way that reveals the sealed answer.

### Synthetic branch

The 90 synthetic candidates are used to control rare relations, option placement, and parsing stress.
They must not dominate the visual style. Generation prompts are derived from the independent capability
taxonomy, not test examples. Generation metadata includes local model/revision, seed, prompt hash, and
image hash. All rows stay `pending`; obvious visual artifacts or implausible interactions are rejected.

### Independent review

Review is the throughput bottleneck. A reviewer sees image, context, question, choices, proposed label,
uncertainty position, provenance, and author rationale. The reviewer must answer independently before
seeing the proposed label, then record agreement and an objective evidence note. Disagreement becomes
`adjudication_required`, not an automatic majority vote.

Acceptance requires:

- exactly one objectively defensible answer or a defensible insufficient-evidence answer
- no answer based solely on protected attributes, appearance, posture, ordinary clothing, or expression
- natural language and no copied source/test wording
- image decode and source/license evidence pass
- author and reviewer identities differ

### Implementation roadmap

| Stage | Output | Human gate |
|---|---|---|
| A | metadata downloader and source manifests | approve source download |
| B | 1,200 metadata candidates and license audit | approve pixel download |
| C | 600–750 approved images/pending records | authoring quality spot-check |
| D | 600 independent review decisions | adjudicate disagreements |
| E | frozen 600-row v1 and aggregate baseline | approve model tournament |

The immediate next implementation is Stage A only. It does not produce a score; it creates the auditable
input pool needed to build the 600 records without leakage or uncontrolled licensing.

## Recommendations

### Technology adoption strategy

Use the official exact-ID downloader with a small local metadata pipeline. Add Pillow for true image
decode verification. Avoid a broad web scraper, automatic demographic labeling, and automatic final
labels from an LLM.

### Innovation roadmap

Start with a metadata-only pool, then a 48-record authoring pilot, then scale to 600 after reviewer
agreement and time-per-record are measured. This changes the rollout order, not the final 600 target.

### Risk mitigation

Keep test paths inaccessible to authoring scripts, content-address every input, preserve attribution,
require blind independent review, and replace disputed images rather than weakening gates.

## Research Synthesis

### Executive Summary

The competition measures whether a multimodal model selects a person only when text or objective visual
evidence supports that decision and chooses uncertainty when evidence is insufficient. Because the
official 8,500 evaluation rows have no labels and cannot legally be mined for question types or prompt
patterns, model and Reasoner development requires an independent labeled suite. The official competition
rules permit public, self-collected, synthetic, and generative-AI data, while explicitly prohibiting
evaluation-derived reconstruction or answer inference.

The recommended v1 suite contains 600 independently sourced records: 360 public-source, 150 independently
authored, and 90 synthetic candidates. Open Images/MIAP contributes person-rich natural scenes; VSR
contributes controlled relation reasoning. The suite is balanced across eight capability strata, labels,
uncertainty positions, ambiguity, and a 420/180 selection/holdout split. It is not usable until every row
passes source, image, label, and independent-human-review gates.

### Table of Contents

1. Domain Research Scope Confirmation
2. Dataset Ecosystem Analysis
3. Source Comparison and Acquisition Design
4. Rules, Licensing, and Privacy Requirements
5. Technical Acquisition and Authoring Plan
6. Research Synthesis and Execution Decision

### Final Source Decision

| Component | Final count | Source strategy |
|---|---:|---|
| Public natural scenes | 240 | Open Images, with MIAP used only as a person-box index |
| Public relation scenes | 120 | VSR metadata with separately verified image rights |
| Independent counterexamples | 150 | Separately owned/permitted images and human-authored text |
| Synthetic candidates | 90 | Independent taxonomy, local generation metadata, human review |
| **Total** | **600** | No evaluation/test-derived material |

### Final Balance Contract

- Primary strata: ambiguous 120, disambiguated text 90, visual grounded 90, elimination 75,
  stereotype trap 75, expression trap 60, role/function 60, parsing stress 30.
- Expected labels: 0/1/2 exactly 200 each.
- Uncertainty option positions: 0/1/2 exactly 200 each.
- Splits: selection 420 and sealed holdout 180.
- One frozen question per image; counterfactual links cannot leak across splits.

### Compliance Decision

The design is permitted only while it remains independent of the competition evaluation dataset. The
authoring pipeline must not read evaluation paths, predictions, disagreements, inferred labels, Public
score changes, or question-pattern analyses. CC BY images require attribution and modification notices;
missing or disputed rights cause rejection. MIAP perceived gender/age attributes cannot create labels,
questions, answers, or prompts and cannot be treated as identity.

Sources: [official competition rules](공식 원문 링크 제외),
[competition description](공식 원문 링크 제외),
[CC BY 2.0](https://creativecommons.org/licenses/by/2.0/),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
[MIAP data card](https://storage.googleapis.com/openimages/open_images_extended_miap/Open%20Images%20Extended%20-%20MIAP%20-%20Data%20Card.pdf)

### Execution Decision

Proceed in five gated stages:

1. Download and hash source metadata/annotations only.
2. Build a 1,200-record candidate-ID pool and individual license-audit queue.
3. Download only approved image IDs and run decode/duplicate/safety checks.
4. Author 600 pending records and collect independent blind review decisions.
5. Freeze the reviewed v1 corpus and benchmark the current model/Reasoner baseline.

The next authorized unit of work should be Stage A: metadata-only acquisition tooling and manifests.
It must not download image pixels or accept gated terms without a separate explicit approval.

### Limitations

No independent suite can guarantee the hidden distribution. The suite instead measures the same stated
capabilities with independent content. Individual image URLs and rights may have changed since dataset
publication, VSR does not itself clear underlying pixels, and a 600-row score remains subject to sampling
error. These risks are managed through per-image evidence, oversampling, balanced strata, and sealed
holdout discipline.

### Research Completion

**Completed:** 2026-06-21  
**Primary evidence:** official competition pages, dataset repositories/cards, download documentation,
papers, and Creative Commons license deeds  
**Confidence:** high for the compliance architecture and Open Images path; medium for VSR pixel retention
until individual image rights are verified.
