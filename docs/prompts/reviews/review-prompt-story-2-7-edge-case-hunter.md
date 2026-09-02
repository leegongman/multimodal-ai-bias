# Story 2.7 Edge Case Hunter Review Prompt

Use `bmad-review-edge-case-hunter`.

Inspect the project and exhaustively walk every branch and boundary introduced by the Reasoner v3 option-index implementation. Review the implementation/test files listed in `docs/history/stories/2-7-implement-reasoner-v3-option-index-contract.md` under `File List`.

Pay particular attention to:

- `schema_mode` values, defaults, and prompt-version routing.
- v1/v2/v3 prompt and parsed-artifact mixing.
- exact JSON types, especially `bool` versus `int`.
- invalid rows carrying lineage fields.
- v2 artifacts reaching active submission or verifier paths.
- final-line parsing, duplicate keys, Unicode, CSV header/order, empty fields, and no-clobber publication.
- semantic combinations of label, uncertainty index, signal, and evidence type.
- CLI behavior for explicit v1/v2 prompt templates.

Report only unhandled edge cases. Each finding must include severity, exact file/line evidence, a reproducer or failing input, and expected safe behavior.
