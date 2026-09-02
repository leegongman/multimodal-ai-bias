# Shadow Private authoring boundary

`record-template.json` is an unreviewed authoring template. Copy one object per JSONL line and
keep its source independent from official evaluation/test data, model disagreements, and leaderboard
feedback. `review-template.json` records a blind decision by a human other than `author_id`.
`adjudication-template.json` resolves `adjudication_required` rows through a second human who is
different from both the author and first reviewer.

Do not change `review_status` to `reviewed` or `adjudicated` until that review occurred. Synthetic or
generated rows remain `pending` until independent human review. Shadow records must never be used for
training or prompt examples.

Start with a 30–50 row pilot exported by `data/shadow-private/pending-v1/review.html`. Apply it with
`shadow-apply-reviews`; partial results intentionally write an auditable report and exit non-zero.
Only a complete 600-row human decision file plus all required adjudications can produce
`promotion_ready=true`. Never edit `pending-v1` in place or treat the generated proposal as review.

On macOS, double-click `scripts/serve-shadow-review.command`, keep its Terminal window open, and
visit `http://127.0.0.1:8765/data/shadow-private/pending-v1/review.html`. This avoids `file://` fetch
restrictions and serves the review records, image pool, and translation vocabulary from the project
root.
The review screen renders the complete Korean translation vocabulary from
`review-ko-translations.json` while retaining the original English underneath for audit. The
translation layer never reads or reveals the proposed label before the reviewer submits an answer.
