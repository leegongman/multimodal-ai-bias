# Epic 4 Context: Private-Generalization Validation and Candidate Selection

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Build an evaluation-set-independent, reviewed, frozen local validation system that measures the competition task's ambiguous/resolvable behavior, prevents Public-only selection, and supports reproducible model, Reasoner, image, engine, and Verifier comparisons before final readiness. Story 4.3 was deferred by the user on 2026-06-21; all Epic 4 work is frozen until a new explicit unlock.

## Stories

- Story 4.1: Define Local Validation Dataset Schema and Subsets
- Story 4.2: Acquire or Author Shadow Private Samples and Provenance
- Story 4.3: Independently Review, Adjudicate, and Balance Samples
- Story 4.4: Freeze Selection and Sealed-Holdout Version
- Story 4.5: Compute Robust Validation Metrics
- Story 4.6: Implement Frozen Tournament Harness and Experiment Contract
- Story 4.7: Run Diagnostic-48 and Reasoner-Only Candidate Selection
- Story 4.8: Integrate Conditional InternVL3-14B Performance Candidate
- Story 4.9: Evaluate Conditional Qwen2.5-VL-32B-AWQ Candidate
- Story 4.10: Run Sealed Shortlist and Verifier A/B
- Story 4.11: Validate Shortlist Runtime and Memory
- Story 4.12: Compare Candidate Runs Without Public-Only Optimization
- Story 4.13: Select Candidate and Record Promotion Rationale

## Requirements & Constraints

- Keep diagnostic-48 separate from the 300–600 sample promotion corpus; diagnostic results never rank candidates.
- Every Shadow sample needs immutable ID, decodable image/hash, context, question, exactly three ordered answers, expected/uncertainty indices, ambiguity consistency, subset tags, provenance, license/permission, author, independent reviewer, review status, and split.
- Required subsets are ambiguous, disambiguated text, visual grounded, elimination, stereotype trap, expression trap, role/function, and parsing stress; each needs at least 30 samples.
- Uncertainty positions 0/1/2 each cover at least 30%; ambiguous and resolvable classes each contain at least 120 samples.
- Corpus size is 300–600. Sealed holdout is at least 30% and 120 samples. Dataset, images, split, schema, and experiment contracts are hashed before ranking.
- Evaluation/test wording, patterns, question-type distributions, images, or inferred answers must not influence validation creation. Public, self-authored, self-collected, synthetic, or permitted generated sources require complete provenance and legal use. Generated labels remain pending until independent human review.
- Validation data is evaluation-only, never training/fine-tuning data. Opening sealed sample-level content for tuning invalidates that holdout version.
- Code uses Python and local/offline inference. Remote model APIs are forbidden. Public score is a secondary sanity signal only.

## Technical Decisions

- Use explicit schemas and fail-closed loaders for labels, vocabularies, image decode/hash, provenance, review separation, and split status.
- Preserve rejected/disputed/reviewed/adjudicated history instead of rewriting records in place.
- Freeze immutable versioned manifests; any sample, label, or split change creates a new version.
- Report local balanced accuracy, ambiguous/resolvable accuracy, worst subset, uncertainty-position accuracy, unknown/person over-selection, stereotype/expression errors, semantic/parse/image/unresolved failures, Verifier flip categories, average/p95 latency, peak VRAM, and projected full runtime.
- Candidate comparisons freeze dataset/split, prompt/schema, model revision, image budget, engine, decoding, seed, Verifier configuration, order, and metric implementation. A diagnostic A/B changes only one material factor.
- Build the 600-row corpus from 360 public-source, 150 independently authored, and 90 synthetic pending candidates; use 420 selection and 180 sealed-holdout rows with exact label and uncertainty-position balance.
- Use Open Images/MIAP as the primary person-rich metadata source and VSR as a controlled relation source. MIAP perceived gender/age attributes may select coverage only and must never enter labels, questions, answers, records, or prompts.
- Acquisition is staged: metadata/annotations and hashes first, candidate-ID/license audit second, approved pixels third, authoring and blind review fourth. Pixel download requires a separate explicit human approval.
- Preserve source record IDs, original landing/pixel URLs, creator/title/license attribution, retrieval time, source checksum, local SHA-256, and modification details. Reject missing or disputed rights rather than weakening gates.
- The acquisition and authoring pipeline must not read official evaluation paths, predictions, disagreements, inferred labels, leaderboard movement, or test-pattern analysis.

## Cross-Story Dependencies

Schema precedes acquisition; acquisition precedes independent review; reviewed balanced data precedes freeze; frozen manifests precede metrics and tournament execution. Human review cannot be replaced by generated approval. Candidate promotion and sealed evaluation cannot start until the corpus and experiment contract are frozen.
