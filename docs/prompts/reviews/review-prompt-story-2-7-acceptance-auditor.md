# Story 2.7 Acceptance Auditor Review Prompt

Review the current implementation against:

- `docs/history/stories/2-7-implement-reasoner-v3-option-index-contract.md`
- `_bmad-output/specs/spec-reasoner-v3-contract/SPEC.md`
- `_bmad-output/specs/spec-reasoner-v3-contract/output-contract.md`

Inspect every implementation/test file listed in the Story's `File List`. Check every Acceptance Criterion and task for actual implementation evidence. Do not accept checked boxes or passing tests as proof without tracing the relevant runtime path.

Report findings as a Markdown list. Each finding must contain:

- One-line title and severity.
- Violated AC or constraint.
- Exact file/line evidence.
- Why the current tests do not catch it, if applicable.
- Minimal corrective action.

Specifically verify that active/default v3 cannot silently consume v2 artifacts, explicit v2 A/B remains usable but isolated, lineage fields round-trip, invalid output never creates a candidate, submission output contracts remain unchanged, and Epic 3 behavior was not accidentally implemented or altered.
