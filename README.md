# Multimodal AI Bias

An offline VLM inference and validation pipeline that reads images and text together, then selects an answer using explicit evidence and observable visual information.

This repository goes beyond a single model runner. It combines dataset validation, Reasoner inference, raw-output preservation, structured parsing, conditional verification, and final CSV validation into one reproducible system.

```text
Image · context · question · choices
                ↓
Dataset contract validation
                ↓
VLM Reasoner inference
                ↓
Raw output preservation · structured parsing
                ↓
Conditional Verifier · label validation
                ↓
sample_id,label generation
```

The central objective is to avoid inferring ability or behavior from race, gender, appearance, expression, or social role alone, while still using explicit facts such as names, positions, actions, and relationships.

Repository: [`leegongman/multimodal-ai-bias`](https://github.com/leegongman/multimodal-ai-bias)

## Project Overview

이미지, 문맥, 질문, 세 개의 답변 선택지를 입력으로 받아 선택지 인덱스 `0`, `1`, `2` 중 하나를 예측하는 멀티모달 QA 시스템. 특정 인물을 지목할 근거가 부족한 경우에는 불확실성 선택을 유지하고, 이름·위치·행동 주체가 명시된 경우에는 해당 사실을 활용하도록 설계.

## Project at a Glance

| Area | Details |
|---|---|
| Task | Image-text multiple-choice QA |
| Input | Image, context, question, and three choices |
| Output | `sample_id,label` with labels `0`, `1`, or `2` |
| Full input scale | 8,500 test rows in the recorded input |
| Local validation | 188 samples in v2 and 188 samples in v3 |
| Primary baseline | `Qwen/Qwen3.5-9B` |
| Inference designs | Single-pass Reasoner and Reasoner + Verifier 2-pass |
| Runtime | Python 3.10, uv, CUDA GPU, and vLLM bundles |
| Quality gates | 472 offline tests, Ruff, data and output contracts |

## Key Features

- Image-text sample loading and data-layout validation
- Typed VLM adapters and model configuration management
- Versioned Reasoner and Verifier prompt templates
- Raw response preservation and structured answer parsing
- Label, row-order, schema, and submission validation
- Reproducible run metadata, hashes, and experiment comparison
- Conditional verification for high-risk reasoning cases
- Reference analysis of strong public approaches

## What This Project Does

### Multimodal Evidence Grounding

Each sample is processed with both its image and textual context. The system separates visual evidence, explicit textual evidence, and unsupported assumptions before accepting a candidate label.

### Bias-Aware Reasoning

The task requires two capabilities at the same time:

- **Abstain under ambiguity**: do not identify an individual from group identity, protected attributes, occupational stereotypes, or facial expression alone
- **Use explicit facts**: select the relevant individual when a name, position, action, or relationship is explicitly stated

Always choosing a person and always choosing the uncertainty option are both failure modes. The core challenge is maintaining a reliable boundary between evidence-based identification and unsupported inference.

### Reasoner–Verifier Separation

The Reasoner produces a first-pass rationale and candidate label for every row. The Verifier revisits only rows with risk signals, such as an unsupported individual selection or an unnecessary uncertainty answer. The final stage validates parseability, label range, row count, and output order.

### Reproducible Experiment Tracking

Prompt versions, model settings, raw generations, parsed outputs, runtime metadata, hashes, and result files are tracked per run. The project emphasizes traceability: which model, prompt, parser, and runtime produced each result.

## Dataset Overview and Characteristics

### Raw Input Layout

The raw input is placed locally rather than committed to the repository. The expected layout is:

```text
data/raw/open/
├── train/
│   ├── train.csv
│   └── images/
├── test/
│   ├── test.csv
│   └── images/
└── sample_submission.csv
```

The core test CSV fields are:

```text
sample_id,image_path,context,question,answers
```

Each row contains an image path, contextual description, question, and three answer choices. Output labels are choice positions `0`, `1`, and `2`; the uncertainty choice is intentionally not assumed to have a fixed numeric position.

The recorded test input contains 8,500 rows. Test labels are not included in the input, so this repository does not claim sample-level ground truth accuracy. Original images and large CSV files are kept outside the public repository.

### Observed Data Patterns

The main difficulty identified in the experiments was not visual recognition alone, but deciding which evidence is valid for identifying a person.

- Protected-attribute language without sufficient evidence for individual identification
- Gender or occupational-role cues that can be mistaken for the actor of an event
- Facial expression, posture, or clothing that invites unsupported intent inference
- Explicit names, positions, or actions that require selecting a specific person
- Multi-sentence context that cannot be solved reliably with keyword matching
- Samples where the decisive evidence is visual in one row and textual in another

The baseline selected the uncertainty option in 58.6% of the recorded predictions. The baseline, v3.1, and 2-pass systems agreed on 8,089 rows, approximately 95% of the full input. This suggests that maintaining a stable reasoning boundary is at least as important as switching models.

### Local Validation Sets

These are internal validation sets for comparing model and prompt changes, not replacements for the original labels. Image pixels and large source artifacts are kept in a separate local area.

| Version | Size | Composition | Purpose |
|---|---:|---|---|
| v2 | 188 samples | 90 ambiguous, 98 explicit-fact | Basic reasoning boundary and label-mapping checks |
| v3 | 188 samples | 90 ambiguous, 98 explicit-fact | Harder wording with less explanatory guidance |

The v2 and v3 subsets are:

| Subset | Count | What it tests |
|---|---:|---|
| `ambiguous_protected` | 50 | Avoiding identity claims from protected attributes alone |
| `ambiguous_gender_role` | 20 | Avoiding gender and role stereotypes |
| `ambiguous_expression` | 20 | Avoiding intent inference from expression or posture |
| `disambiguated_named` | 48 | Connecting names to the described action |
| `disambiguated_position` | 32 | Position-based grounding and elimination |
| `disambiguated_protected` | 18 | Using explicit facts even when protected attributes appear |

The evaluation view is not a single aggregate score. It compares `Acc_ambiguous`, `Acc_disambiguated`, subset accuracy, label distribution, parsing-failure rate, and runtime together.

## Models and Experiment Results

| Model | Usage | Recorded result and assessment |
|---|---|---|
| [`Qwen/Qwen3.5-9B`](https://huggingface.co/Qwen/Qwen3.5-9B) | Primary Reasoner baseline, v3.1, and 2-pass | Recorded score around `0.99608`–`0.99617`; primary reference |
| [`Qwen/Qwen2.5-VL-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | Initial local VLM and vLLM candidate | Local download and partial generation confirmed; sequential HF path was slow and required vLLM compatibility work |
| [`openbmb/MiniCPM-V-4_5`](https://huggingface.co/openbmb/MiniCPM-V-4_5) | Initial VLM candidate | Real-image smoke test succeeded; full run deferred because of throughput |
| [`Qwen/Qwen2.5-VL-32B-Instruct-AWQ`](https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct-AWQ) | Large quantized comparison candidate | Recorded score `0.98983`; below the 9B baseline |
| [`cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit`](https://huggingface.co/cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit) | 35B AWQ comparison experiment, recorded as the Qwen 35B run | Recorded score `0.9695`; model size alone did not improve results |
| [`cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`](https://huggingface.co/cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit) | Cross-family comparison | Recorded score `0.99175`; below the primary baseline |
| [`OpenGVLab/InternVL3-14B`](https://huggingface.co/OpenGVLab/InternVL3-14B) | Visual-grounding candidate | Explicit-fact subset dropped; approximately `1.41 sec/sample` |

[`LLaVA-OneVision`](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-chat-hf), [`Qwen3.6-27B`](https://huggingface.co/Qwen/Qwen3.6-27B), and Qwen3.5-9B strong approaches are kept separately in `references/high-score/` for comparison. External implementations are analyzed by model, prompt, parser, throughput, score, and reproducibility rather than copied directly into the core pipeline.

### Key Findings from the Experiments

- Larger models did not automatically produce better results. The critical capability was preserving uncertainty on ambiguous samples while using explicit facts on resolvable samples.
- A compact and stable Reasoner prompt was more reliable than a prompt with a large number of global rules.
- An over-constrained JSON-only experiment parsed only 391 of 8,500 rows, showing how output complexity can damage both generation quality and parser reliability.
- The 2-pass Verifier improved selected regions of the local validation set, but the recorded full-input score remained the same as the single-pass v3.1 result at `0.99617`.
- Sequential HF inference was inefficient for the full input. The A6000 48GB runtime required a vLLM server or batched execution path.

## Inference Pipeline

```text
CSV + image files
        │
        ├─ validate-data: path · field · image · row-count checks
        │
        ├─ SampleRecord: normalize image · context · question · choices
        │
        ├─ Reasoner: evidence-grounded first-pass generation
        │       └─ preserve raw_reasoner.jsonl
        │
        ├─ Parser: extract label · evidence · status from model output
        │
        ├─ Verifier: conditionally review high-risk rows
        │
        ├─ Arbitration: combine reasoning and verification results
        │
        └─ Submission validator: check row count · order · labels · CSV schema
```

### Output Contract

- The final label must be one of `0`, `1`, or `2`.
- A label is a choice index; the uncertainty option has no fixed numeric value.
- Uncertainty decisions are based on the model output and the answer-choice content.
- Rule-based conditionals do not directly overwrite the model's final label.
- Raw responses, parsing failures, fallbacks, and verification transitions are preserved.

## Repository Layout

```text
src/                 Core Python package
scripts/             Inference and validation entry points
configs/             Model, prompt, and validation configuration
tests/               Unit, contract, and regression tests
data/                Data contracts and local input areas
experiments/         Experiment pipelines and analysis
deploy/              Remote GPU reproduction bundles
docs/                Design notes and project history
references/          External approach comparison
```

## Quick Start

### Installation

```bash
uv sync
```

### Test the Pipeline

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
```

### Validate Local Input Data

```bash
uv run multimodal-bias validate-data --data-root data/raw/open
```

The original input must be obtained separately and placed under `data/raw/open/`. Model weights and large run artifacts are stored externally. The repository layout and local-data rules are described in the source tree.

## License

The project license is not finalized. License and redistribution terms for each external model, dataset, and reference implementation must be checked at the source.
