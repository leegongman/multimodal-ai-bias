---
stepsCompleted: [1]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Next VLM model for the unchanged Reasoner v3 pipeline'
research_goals: 'Select the next single-GPU model experiment after Qwen3.5-9B scored 0.94, changing only the model while deferring runtime optimization'
user_name: 'gongman'
date: '2026-06-20'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-06-20
**Author:** gongman
**Research Type:** technical

---

## Research Overview

[Research overview and methodology will be appended here]

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** Next VLM model for the unchanged Reasoner v3 pipeline
**Research Goals:** Select the next single-GPU model experiment after Qwen3.5-9B scored 0.94, changing only the model while deferring runtime optimization

**Technical Research Scope:**

- Compare current official vision-language checkpoints that can preserve the existing image-plus-text Reasoner v3 contract.
- Prioritize expected task quality over immediate 70-minute optimization, while retaining single-A6000 feasibility as a hard implementation constraint.
- Keep prompt, parser, output schema, deterministic decoding, and submission pipeline fixed so the model is the only experimental variable.
- Verify model architecture, loading requirements, vLLM support, memory implications, and licensing from current primary sources.
- Select one next experiment and one fallback rather than producing an unranked catalog.

**Research Methodology:**

- Current web data with primary-source verification
- Cross-check critical compatibility and memory claims
- Separate documented facts from inference
- Record uncertainty where no directly comparable benchmark exists

**Scope Confirmed:** 2026-06-20

## Technology Stack Analysis

### Programming Language and Request Contract

The experiment stack should remain Python-based and preserve the existing OpenAI-compatible multimodal chat request: one system message, one user message containing an image URL plus text, deterministic decoding, and a JSON-schema response format. This makes native vLLM OpenAI API support more important than a model's standalone Transformers demo. Qwen3-VL documents this exact image-url request pattern, while MiniCPM-V 4.6 documents both Transformers-native and vLLM serving paths.

Sources: [Qwen3-VL-8B-Instruct model card](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct), [MiniCPM-V 4.6 model card](https://huggingface.co/openbmb/MiniCPM-V-4.6)

### Model Frameworks and Candidate Families

- **Gemma 4 12B IT:** a newly released 11.95B Unified multimodal instruction model with native system-role support and configurable thinking. The official BF16 checkpoint is approximately 24 GB, making it plausible on a 48 GB A6000 while leaving materially less KV-cache headroom than the 9B baseline. Current vLLM documentation explicitly supports `Gemma4UnifiedForConditionalGeneration` and names `google/gemma-4-12B-it`; therefore it is not merely a Transformers-only candidate. Its recency and larger dense capacity make it the strongest score-first experiment, subject to a real server-load and structured-output smoke.
- **Qwen3-VL-8B-Instruct:** Apache-2.0, native Transformers and vLLM examples, approximately 17.5 GB of BF16 checkpoint files. It is operationally the closest adapter match, but its expected quality advantage over the already-tested newer Qwen3.5-9B is uncertain; it is therefore a compatibility fallback, not the leading quality experiment.
- **InternVL3.5-8B-Instruct:** approximately 8.5B total parameters (0.3B vision plus 8.2B language), Apache-2.0, and explicitly listed by current vLLM documentation through `InternVLChatModel`. Its distinct visual encoder and training recipe provide the strongest useful model-family contrast while retaining a similar parameter class.
- **MiniCPM-V 4.6:** exceptionally efficient and natively documented for vLLM, but it is built on a Qwen3.5-0.8B language backbone. Its own card positions multimodal capability around Qwen3.5-2B on several benchmarks, so it is primarily a speed candidate rather than the most credible route above the 9B baseline's score.

Sources: [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4), [Gemma 4 12B IT checkpoint](https://huggingface.co/google/gemma-4-12B-it), [InternVL3.5-8B-Instruct model card](https://huggingface.co/OpenGVLab/InternVL3_5-8B-Instruct), [vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models.html), [MiniCPM-V 4.6 model card](https://huggingface.co/openbmb/MiniCPM-V-4.6)

### Model and Artifact Storage

Every candidate must use an official immutable Hugging Face snapshot with a recorded revision, local offline loading, and a separate run directory. Model weights, prompt hash, raw model output, parsed rows, prediction hash, runtime, GPU telemetry, Public score, and leaderboard rank must remain attributable to one model experiment. No candidate-specific post-processing may alter the Reasoner v3 decision contract.

### Development and Validation Tools

The existing vLLM 0.17.1 server and OpenAI client remain the reference path. Before a full run, each candidate needs three gates: successful native multimodal server load, valid structured output on real images, and a fixed ordered subset confirming that the model follows the unchanged v3 schema. Current vLLM documentation explicitly lists InternVL 3.5 and Qwen multimodal families; MiniCPM-V 4.6 additionally provides its own vLLM launch command.

Source: [vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models.html)

### GPU Platform

The target remains one 48 GB RTX A6000. BF16 8B-class checkpoints are plausible without quantization, but memory feasibility must include the vision encoder, KV cache, image-token expansion, and 32K server context—not just weight size. The next experiment should start in BF16 to avoid introducing quantization as a second changed variable.

### Technology Adoption Direction

Current model releases increasingly provide native `transformers` image-text classes and vLLM OpenAI-compatible serving instead of requiring custom chat code. Qwen3-VL and MiniCPM-V 4.6 already expose standard image-text interfaces, while vLLM supports InternVL3.5's established custom architecture. For this project, native structured-output behavior remains an empirical gate: architecture support does not by itself prove that every JSON-schema constraint is honored.

### Stack-Level Preliminary Ranking

1. **Gemma 4 12B IT** — strongest score-first experiment; newest architecture and larger dense capacity, with explicit vLLM multimodal support.
2. **InternVL3.5-8B-Instruct** — strongest established non-Qwen fallback and useful architecture-family contrast.
3. **Qwen3-VL-8B-Instruct** — lowest integration risk, but weak expected upside over Qwen3.5-9B.
4. **MiniCPM-V 4.6** — strongest efficiency option, but unlikely to be the best score-first choice.

Confidence is high for documented framework compatibility and parameter class, but only moderate for the quality ordering because no public benchmark directly represents this competition's bias-sensitive three-choice task.

### Gemma 4 12B Runtime Opportunity

Gemma 4 12B has two documented acceleration mechanisms. Its Unified architecture removes a separate vision encoder and projects raw image patches directly into the decoder embedding space, which is intended to reduce multimodal latency. It also has an official approximately 0.4B-parameter MTP assistant checkpoint for speculative decoding. Google reports up to 3x decoding speedup with exact target-model quality, and vLLM exposes a Gemma 4-specific MTP serving path.

This does not imply a 3x end-to-end speedup for this competition. MTP accelerates autoregressive output decoding, whereas each sample still pays image processing and prompt-prefill cost. Reasoner v3 produces short JSON outputs, so image/prefill may dominate. In addition, the 12B target is larger than the 9B baseline. The appropriate gate is therefore a fixed real-image subset measured both with and without the official MTP assistant; no end-to-end runtime claim should be made from the vendor's decoding-only maximum.

Sources: [Gemma 4 12B MTP assistant](https://huggingface.co/google/gemma-4-12B-it-assistant), [vLLM Gemma 4 MTP documentation](https://docs.vllm.ai/en/v0.21.0/features/speculative_decoding/mtp/), [Gemma 4 overview](https://ai.google.dev/gemma/docs/core)
