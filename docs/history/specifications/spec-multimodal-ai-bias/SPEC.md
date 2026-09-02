---
id: SPEC-multimodal-236722-multimodal-ai-bias
companions:
  - strategy.md
  - validation-strategy.md
  - compliance-references.md
  - architecture-diagrams.md
sources:
  - ../../research/technical-multimodal-236722-multimodal-ai-bias-research-2026-06-18.md
  - ../../../Multimodal_236722_평가_요구사항_정리.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only.

# Multimodal 236722 Multimodal AI Bias Solution

## Why

This spec exists to meet a competition mandate and capture a Private/Hidden generalization opportunity: build a reproducible multimodal QA system that predicts `0/1/2` labels for Multimodal 236722 while avoiding Public leaderboard overfit, stereotype-based guessing, and rule violations.

## Capabilities

- id: CAP-1
  intent: The system can ingest the official `open.zip` structure and produce predictions for every `test.csv` sample.
  success: Given valid competition data, the system emits one UTF-8 CSV with exactly `sample_id,label`, 8,500 rows, and labels restricted to `0`, `1`, `2`.

- id: CAP-2
  intent: The system can produce evidence-grounded answers that distinguish resolvable questions from genuinely uncertain questions.
  success: On the project validation set, reports include separate ambiguous accuracy, disambiguated accuracy, local balanced accuracy, and failure counts for over-uncertainty and unsupported person selection.

- id: CAP-3
  intent: The system can prevent protected-attribute and appearance-only cues from deciding subjective person judgments.
  success: On stereotype-trap and expression-trap validation subsets, every audited wrong answer is traceable to a logged model reason rather than an unlogged rule or silent fallback.

- id: CAP-4
  intent: The system can selectively re-evaluate low-confidence or high-risk answers before final label emission.
  success: Conditional verification changes are logged with before/after labels, reasons, trigger category, and validation impact; no final label is produced by pure majority vote or deterministic rule mapping.

- id: CAP-5
  intent: The system can select submission candidates using Private-generalization criteria instead of Public-only tuning.
  success: Candidate promotion requires local robust validation results, parse/image-load failure rates, runtime measurements, and a submission rationale that treats Public score as a sanity signal.

- id: CAP-6
  intent: The system can demonstrate competition-rule compliance for models, data, inference, and outputs.
  success: Each candidate run has a compliance record covering model release cutoff, license/source, no remote API inference, external data provenance, offline execution, and LLM-generated final reasoning.

- id: CAP-7
  intent: The system can generate a second-round-ready artifact set if the team qualifies.
  success: The workspace contains separated train/inference code, environment/version records, model/data references, raw inference logs, and enough run metadata to reproduce the selected Private submission within expected variance.

- id: CAP-8
  intent: The operator can prove that the selected local GPU path can safely produce a compliant full submission before production starts.
  success: Stable ten-gate evidence records 10/10, publishes `GPU_SUBMISSION_READY`, and explicitly notifies the operator with candidate, command, and runtime projection; any failed gate suppresses readiness and production.

## Constraints

- Use Python for competition code.
- Use only models whose official open-source weights were public by 2026-05-31.
- Do not use OpenAI API, Gemini API, Hugging Face Inference API, Together AI, OpenRouter, or any remote model API for inference.
- Final label decisions must be derived from generated LLM text, not from pure rules, pure majority voting, fixed answer lists, or deterministic post-hoc mapping.
- Do not derive training data, prompt templates, rules, or examples from the evaluation set's question types, choice patterns, wording, or inferred answers.
- Treat `test.csv` and images as inference-only inputs.
- Target the organizer reference environment: RTX A6000 48GB, Python 3.10, CUDA 12.4, PyTorch 2.6.0, Ubuntu 20.04.
- Keep final inference practical for the organizer guidance: about 0.5 seconds/sample, about 70 minutes for 8,500 test samples, about 13 minutes for 1,500 Hidden samples unless a slower model is explicitly justified and verified.
- Public leaderboard results must not be the sole model, prompt, or threshold selection criterion.
- Submission CSV and code comments must be UTF-8.

## Non-goals

- Do not build a web UI, dashboard, or interactive labeling product.
- Do not optimize only for Public leaderboard rank.
- Do not require fine-tuning before a strong inference baseline exists.
- Do not make 27B two-pass inference the default unless runtime, memory, compliance, and validation all justify it.
- Do not manually infer, leak, or reconstruct test answers.

## Success signal

The team can run one documented offline command path from competition data to a compliant submission CSV, with logs proving evidence-grounded LLM decisions, local robust validation, runtime feasibility, and rule compliance. The selected submission is chosen because it is expected to generalize to Private/Hidden, not because it only improved Public score.

## Assumptions

- The primary implementation direction is a corrected Qwen2.5-VL-7B control followed by a staged local-model tournament; exact winning revision remains open until frozen Shadow Private and A6000 gates complete.
- Reasoner and Verifier outputs use answer-choice indexes only and explicitly generate `uncertainty_option_index`; no numeric label has an inherent semantic class.
- Independent validation consists of a separate diagnostic-48 and a frozen 300–600 sample Shadow Private suite with a sealed holdout.

## Open Questions

- Which eligible candidate and exact revision wins the frozen Shadow Private, verifier, runtime, and compliance gates?
- What GPU environment will be used for local full-test inference before Multimodal submission?
- How will the independent validation set be sourced or generated without using evaluation-set patterns?
- If the team reaches second-round review, who owns the PDF solution deck and student-status evidence packaging?
