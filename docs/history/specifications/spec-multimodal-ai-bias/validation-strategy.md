# Validation Strategy

## Purpose

Validation exists to protect Private/Hidden generalization. Public score is not enough because the official metric averages ambiguous and disambiguated accuracy, while group membership is hidden.

## Required Validation Subsets

Validation has two separate tiers: `diagnostic-48` for mapping/image/template/engine defects and a frozen `shadow-private-300-600` for promotion. Diagnostic results are never tournament ranking scores. The Shadow Private suite has selection and sealed-holdout splits; sealed holdout is at least 30% and at least 120 samples.

The Shadow Private suite must contain explicit subset labels:

| subset | purpose |
|---|---|
| `ambiguous` | Information is insufficient; uncertainty should be selected. |
| `disambiguated_text` | Context states the answer or its opposite clearly. |
| `visual_grounded` | Objective image evidence such as action, object, readable text, location, badge, or uniform identifies the answer. |
| `elimination` | One person's stated fact or opposite fact determines the other. |
| `stereotype_trap` | Protected attributes tempt an unsupported answer. |
| `expression_trap` | Expression, posture, or clothing tempts a subjective judgment without valid evidence. |
| `role_or_function` | Stated role or duty identifies the person. |
| `parsing_stress` | Choice text and uncertainty wording vary enough to test output parsing. |

## Metrics

Each candidate report must include:

- local balanced accuracy
- ambiguous accuracy
- disambiguated accuracy
- worst-subset accuracy
- unknown over-selection rate
- person over-selection rate
- stereotype-trap error count
- expression-trap error count
- verifier trigger count and flip categories
- parse failure rate
- image-load failure rate
- uncertainty-position accuracy for index 0/1/2
- semantic-consistency and unresolved rates
- beneficial, harmful, and no-effect Verifier flips
- peak VRAM and projected 8,500-row full-path runtime
- average and p95 seconds/sample

## Candidate Promotion Rule

A candidate cannot be promoted solely because Public improves. Promotion requires a written decision that compares:

- local robust validation against the previous candidate
- ambiguous/disambiguated balance
- worst-subset regressions
- runtime and memory feasibility
- compliance status
- Public score, only as a secondary sanity signal

## Validation Data Safety

Validation examples may be public, self-authored, synthetic, or generated with allowed tools only if they are not derived from evaluation-set wording, choice patterns, question types, images, or inferred answers. Test data must not be used to create validation examples or prompt rules.

The Shadow Private suite contains 300–600 reviewed samples. Each required subset has at least 30 samples; uncertainty option positions 0/1/2 each cover at least 30% of the suite; ambiguous and resolvable classes each contain at least 120 samples. Dataset, image, split, and schema manifests are hashed before tournament execution. Opening sealed sample-level results for tuning invalidates that holdout version.
