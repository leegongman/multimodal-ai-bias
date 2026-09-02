## Deferred from: code review of 2-4-run-reasoner-inference-and-preserve-raw-outputs (2026-06-18)

- Installed console-script test may resolve a stale/global executable (`tests/test_cli.py:437`). This predates Story 2.4 and should be addressed separately by making the test resolve the checkout's installed script/environment deterministically.

## Deferred from: code review of 2-5-parse-reasoner-outputs-into-structured-predictions (2026-06-18)

- Installed console-script test may resolve a stale/global executable (`tests/test_cli.py:537`). This predates Story 2.5 and remains tracked for deterministic checkout-local executable resolution.
- Lazy-import test removes adapter modules from shared `sys.modules` without restoring them (`tests/test_model_adapter.py:181`). This predates Story 2.5 and should be isolated in a subprocess or restore module state.
