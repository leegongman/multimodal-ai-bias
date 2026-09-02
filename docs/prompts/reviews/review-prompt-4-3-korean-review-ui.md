# Adversarial Review Request: Story 4.3 Korean Review UI

Review the following change without assuming the implementation is correct. Report only concrete,
actionable findings with severity, file, and line. Do not modify files.

## Intent

Make the existing blind human-review UI understandable to a Korean reviewer by showing Korean
translations for every dataset context, question, and answer while preserving the original English
for audit. The translation layer must not expose or infer the proposed label before submission and
must not alter exported review decisions.

## Changed Files

- `configs/validation/review-ko-translations.json`
- `data/shadow-private/pending-v1/review.html`
- `tests/test_shadow_review.py`
- `configs/validation/README.md`
- `scripts/serve-shadow-review.command`

## Review Focus

1. Translation semantics: direction words, negation, elimination, ambiguity, and role wording must
   preserve the English meaning without introducing answer cues that were absent from the source.
2. Blindness: no proposed label or expected-label-derived content may appear before independent
   answer submission.
3. Contract preservation: exported JSONL fields and values must remain unchanged.
4. Coverage/failure behavior: every phrase in the 600-row dataset must be translated; missing or
   failed translation loads must be visible and fail safely.
5. Local serving: the launcher URL/root and relative records, image, and translation paths must all
   resolve from a clean macOS launch.

## Existing Verification

- `pytest -q tests/test_shadow_review.py tests/test_shadow_validation.py tests/test_shadow_acquisition.py tests/test_cli.py` → 71 passed
- Ruff check/format for `tests/test_shadow_review.py` → passed
- Extracted review-page JavaScript syntax check → passed
- HTTP HEAD for page, records, and translation JSON → 200 for all three
