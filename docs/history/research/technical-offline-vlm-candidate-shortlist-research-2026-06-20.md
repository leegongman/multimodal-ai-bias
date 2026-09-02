---
stepsCompleted: [1, 2]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: '2026 SKKU Multimodal AI Bias Challenge offline VLM candidate shortlist'
research_goals: 'Eligible, performant VLM shortlist for identical Reasoner v3 mapping under RTX A6000 48GB constraints'
user_name: 'gongman'
date: '2026-06-20'
web_research_enabled: true
source_verification: true
---

# Research Report: Offline VLM Candidate Shortlist

**Date:** 2026-06-20
**Author:** gongman
**Research Type:** technical

---

## Research Overview

[Research overview and methodology will be appended here]

## Technical Research Scope Confirmation

**Research Topic:** 2026 SKKU Multimodal AI Bias Challenge offline VLM candidate shortlist

**Research Goals:** Select 3–5 eligible and technically credible VLM candidates for identical Reasoner v3 mapping.

**Technical Research Scope:**

- Architecture analysis — model size, vision encoder, generation stack, and memory fit
- Implementation approaches — official processor/chat template and local adapter compatibility
- Technology stack — RTX A6000 48GB, Python 3.10, CUDA 12.4, PyTorch 2.6.0
- Integration patterns — offline weights, official serialization, strict Reasoner v3 output
- Performance considerations — 8,500 samples in approximately 70 minutes

**Research Methodology:**

- Current official model cards, repositories, papers, and competition rules
- Release date and license verification against the 2026-05-31 cutoff
- Confidence levels where A6000 throughput evidence is unavailable
- Research and shortlist only; no download, implementation, or execution

**Scope Confirmed:** 2026-06-20

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technology Stack Analysis

### Programming Language and Runtime

- 기준 언어는 평가가 요구하는 Python이며, 대상 실행 환경은 Python 3.10, CUDA 12.4, PyTorch 2.6.0, Ubuntu 20.04, RTX A6000 48GB로 고정한다.
- PyTorch 2.6은 2025-01-29 공개되었으며, 후보 모델은 이 버전에서 공식 또는 보수적인 호환 경로가 있어야 한다.
- CUDA 확장이나 커스텀 연산자를 필수로 요구하는 모델은 PyTorch 2.6 ABI 및 Ubuntu 20.04 빌드 위험 때문에 후순위로 둔다.

Sources: [Multimodal rules](공식 원문 링크 제외), [PyTorch 2.6 release](https://pytorch.org/blog/pytorch2-6/)

### Model Framework and Serialization

- 공통 기준 구현은 Hugging Face Transformers의 `AutoProcessor`와 `AutoModelForImageTextToText` 또는 후보가 공식 지정한 동등 클래스를 사용한다.
- Reasoner v3의 의미 내용은 모델 간 동일하게 유지하고, 모델별 차이는 공식 `Processor.apply_chat_template()`가 처리하는 이미지 토큰·role 토큰·generation prefix로 제한한다.
- 잘못된 chat control token은 성능을 크게 훼손할 수 있으므로, 수동 문자열 조합보다 체크포인트가 제공하는 공식 chat template를 필수 증거로 취급한다.
- 멀티모달 processor 결과에 `pixel_values`와 모델별 이미지 메타데이터가 포함되는지 확인해야 한다.

Sources: [Transformers multimodal chat templates](https://huggingface.co/docs/transformers/chat_templating_multimodal), [Transformers chat templates](https://huggingface.co/docs/transformers/en/chat_templating)

### GPU Memory and Precision

- RTX A6000은 48GB GDDR6 ECC 메모리를 제공한다. BF16/FP16으로 안정적으로 적재되는 3B–14B급 dense VLM을 우선 검토한다.
- 20B 이상 모델은 공식 4-bit 체크포인트 또는 검증 가능한 AWQ/BNB 경로가 있을 때만 후보로 유지한다.
- Quantization은 메모리 적합성을 높이지만 정확도와 의존성 위험을 추가한다. 특히 AutoAWQ가 Transformers 버전을 낮출 수 있다는 공식 문서 경고가 있어, native BF16 후보보다 통합 위험을 높게 평가한다.
- `device_map="auto"`와 Accelerate는 적재 보조 수단이지만 CPU/disk offload가 발생하는 후보는 0.5초/샘플 목표에 부적합한 것으로 본다.

Sources: [NVIDIA RTX A6000](https://marketplace.nvidia.com/en-us/enterprise/laptops-workstations/nvidia-rtx-a6000/), [Transformers AWQ](https://huggingface.co/docs/transformers/quantization/awq), [Accelerate big-model inference](https://huggingface.co/docs/accelerate/package_reference/big_modeling)

### Offline Model and Artifact Storage

- 모델, processor, tokenizer, custom code는 실행 전에 로컬 snapshot으로 고정한다.
- `HF_HUB_OFFLINE=1`과 `local_files_only=True`가 가능한 후보만 허용하며, 원격 추론 API나 실행 중 다운로드가 필요한 후보는 제외한다.
- 별도 데이터베이스는 필요하지 않다. 각 실행은 append-only JSONL/CSV와 immutable config/model/prompt/code hash로 보존하고, 제출 레지스트리는 행 단위 CSV 또는 SQLite 인덱스로 관리할 수 있다.

Source: [Transformers offline mode](https://huggingface.co/docs/transformers/v4.49.0/en/installation#offline-mode)

### Execution Engine and Deployment

- 1차 호환성 기준은 in-process Transformers `generate()`이다. 후보별 공식 구현을 가장 직접적으로 재현하고 raw output을 보존하기 쉽다.
- vLLM 등 대체 엔진은 모든 후보가 동일하게 지원되지 않으므로 shortlist의 필수 조건으로 삼지 않는다. 이후 동일 모델 내 속도 최적화 실험으로 분리한다.
- 클라우드는 RTX A6000 48GB 단일 GPU의 오프라인 실행 환경으로 한정한다. 후보 선정 단계에서는 다운로드나 GPU 실행을 하지 않고, 문서상 적합성과 통합 위험만 평가한다.

### Technology Adoption Decision

- **우선 경로:** 공식 Transformers 지원 + 공식 processor/chat template + BF16/FP16 단일 A6000 적재.
- **조건부 경로:** 공식 AWQ/4-bit checkpoint + 고정 가능한 의존성.
- **제외 경로:** API 전용, 공개일/라이선스 불명, 실행 중 네트워크 필요, 비공식 변환만 존재, CPU offload가 필수인 모델.
- 이 스택 결정은 모델 계열별 Reasoner v3 비교에서 prompt semantics를 고정하고 serialization 차이만 모델 고유 변수로 남긴다.

**Confidence:** 공통 프레임워크·오프라인·메모리 기준은 높음. 후보별 실제 8,500행 처리속도는 공식 문서만으로 확정할 수 없어 GPU smoke 전까지 중간 이하로 유지한다.

## Integration Patterns Analysis

### Canonical Reasoner v3 Boundary

모든 후보는 동일한 논리 입력을 받는다.

1. `system`: Reasoner v3 판단 원칙과 strict JSON 계약
2. `user`: 이미지, context, question, 원문 순서의 선택지
3. 모델 공식 processor/chat template가 모델별 control token과 image token을 생성
4. `model.generate()` 또는 공식적으로 동등한 로컬 생성 함수 호출
5. 새로 생성된 assistant text만 분리
6. 공통 v3 parser가 마지막 `FINAL_ANSWER_JSON:` 행을 검증

모델별 prompt 문구를 튜닝하지 않고 직렬화 계층만 바꾸는 것이 모델 효과를 분리하는 핵심이다.

Source: [Transformers multimodal chat templates](https://huggingface.co/docs/transformers/chat_templating_multimodal)

### Integration Class A — Native Transformers Multimodal Template

- **Qwen3-VL-8B-Instruct:** `AutoProcessor` + `AutoModelForImageTextToText` + `processor.apply_chat_template()`가 공식 모델 카드에 직접 제시된다. 별도 remote code 없이 canonical boundary에 가장 가깝다.
- **Gemma 3 12B IT:** 공식 Image-Text-to-Text 체크포인트로 native Transformers 경로를 제공한다. 다만 Gemma 라이선스 검토와 gated-weight 접근 재현성이 추가 조건이다.
- **Llama 3.2 11B Vision Instruct:** 공식 image-text pipeline을 제공하지만 Llama Community License와 image+text의 공식 언어 범위가 영어로 제한된다.

Sources: [Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct), [Gemma 3 12B IT](https://huggingface.co/google/gemma-3-12b-it), [Llama 3.2 11B Vision Instruct](https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct)

### Integration Class B — Transformers with Pinned Custom Code

- **Kimi-VL-A3B-Instruct:** `AutoProcessor.apply_chat_template()`와 `model.generate()`를 사용하지만 `trust_remote_code=True`가 필요하다. 16B total/약 3B active MoE라서 품질·속도 후보로 매력적이나 custom code hash와 의존성 고정이 필수다.
- **InternVL3.5 8B/14B:** 공식 checkpoint에 chat template와 custom code가 포함된다. 이미지 tiling과 `model.chat()` 또는 repository-specific preprocess 경로를 정확히 보존해야 한다.
- **Ovis2.5-9B:** Qwen3-8B 언어 모델과 SigLIP2 vision encoder를 사용하며 공식 `chat_template.json`이 있다. `trust_remote_code=True`이므로 코드 snapshot 검증이 필요하다.
- **Phi-4-multimodal-instruct:** Microsoft가 PyTorch 2.6.0, Transformers 4.48.2, Python 3.10 경로와 image placeholder 형식을 명시한다. 현 평가 환경과 버전 정합성이 높지만 공식 예제는 수동 control token 조립을 포함하므로 v3 adapter 검증이 필요하다.

Sources: [Kimi-VL-A3B-Instruct](https://huggingface.co/moonshotai/Kimi-VL-A3B-Instruct), [InternVL3.5-8B](https://huggingface.co/OpenGVLab/InternVL3_5-8B), [Ovis2.5-9B](https://huggingface.co/AIDC-AI/Ovis2.5-9B), [Phi-4-multimodal-instruct](https://huggingface.co/microsoft/Phi-4-multimodal-instruct)

### Integration Class C — Model-Specific Chat API

- **MiniCPM-V 4.5:** 공식 예제의 중심 경로는 `AutoModel(..., trust_remote_code=True)` 후 `model.chat(msgs=..., tokenizer=...)` 호출이다. Hugging Face pipeline과 vLLM 지원도 표시되지만, Reasoner v3의 system/user 분리와 raw generated assistant text 보존이 공통 adapter에서 정확히 재현되는지 확인해야 한다.
- 이 계열은 기능상 통합 가능하지만 Class A보다 adapter-specific behavior가 크므로 smoke gate를 통과하기 전에는 정식 비교 대상으로 보지 않는다.

Source: [MiniCPM-V 4.5](https://huggingface.co/openbmb/MiniCPM-V-4_5)

### Data Formats and Artifact Interoperability

- 입력: UTF-8 text fields + local image bytes.
- rendered input evidence: 모델별 최종 chat text/token IDs, processor config hash, image preprocessing metadata.
- 생성 원본: UTF-8 JSONL에 assistant raw output과 prompt/image/model hashes 보존.
- 공통 결과: strict v3 parsed CSV와 Multimodal submission CSV.
- 후보가 별도 reasoning block 또는 `<think>`를 출력해도 parser는 마지막 marker만 읽으며, marker 뒤 JSON이 정확하지 않으면 실패로 기록한다.

### Security and Offline Integration

- `trust_remote_code=True` 후보는 실행 시 네트워크를 허용한다는 뜻이 아니라, 사전에 내려받아 hash로 고정한 custom Python code를 로드한다는 뜻으로 제한한다.
- 모든 `from_pretrained` 호출은 local snapshot과 `local_files_only=True`를 사용한다.
- 로컬 vLLM/OpenAI-compatible endpoint를 사용하더라도 네트워크 서비스 의존성을 늘리므로 초기 후보 비교에서는 in-process generation을 우선한다.

### Integration Risk Ranking

1. **낮음:** native Transformers model class + official processor chat template.
2. **중간:** pinned `trust_remote_code` + standard `generate()`.
3. **중상:** custom `model.chat()` + custom image tiling/preprocessing.
4. **높음/제외:** 비공식 변환, 런타임 다운로드, 공식 system role 또는 assistant-text 분리 경로 불명.

**Confidence:** Qwen3-VL과 Phi-4의 공식 통합 경로는 높음. Kimi/InternVL/Ovis/MiniCPM의 v3 exact-system-role 호환성은 실제 smoke 전까지 중간이다.

### Candidate Note — Qwen3.6-27B Two-Pass Proposal

- Qwen3.6-27B는 Qwen 공식 Apache-2.0 image-text checkpoint이며 citation 기준 2026년 4월 공개로 평가 cutoff 이전이다.
- 참가자 제시 Colab 측정치가 Pass1 1.096초/전체 샘플, Pass2 1.510초/전체 샘플이고 두 단계가 순차 실행된다면 총 2.606초/sample이다.
- 8,500건 환산은 Pass1 약 155.3분, Pass2 약 213.9분, 합계 약 369.2분(6시간 9분)이다. 평가 권장 약 70분보다 약 5.27배 길다.
- 일반 규칙 페이지는 0.5초/sample을 `권장` 및 `참고 기준`으로 표현하지만, 2026-06-17 운영진 FAQ는 기준 평가 환경에서 Test 70분·Hidden 13분 기준을 `충족해야` 한다고 명시했다. 최종 평가 적격성에는 FAQ의 더 엄격한 최신 해석을 적용한다.
- `Pass1`/`Pass2`는 Qwen 표준 용어가 아니다. 보통 1차 답변 생성과 2차 검토·수정 호출을 뜻하지만, 정확한 의미와 Pass2 적용 행 수는 해당 참가자의 코드가 필요하다.
- BF16 28B weights는 가중치만 단순 계산해도 약 56GB이므로 48GB A6000에서는 quantization 또는 offload가 필요하다. Colab GPU 종류와 precision/engine/batch/image-token 설정이 없으면 A6000 처리시간으로 환산할 수 없다.

Sources: [Qwen3.6-27B official model card](https://huggingface.co/Qwen/Qwen3.6-27B), [Multimodal runtime rules](공식 원문 링크 제외), [Multimodal runtime FAQ](공식 원문 링크 제외)

### Preliminary Shortlist Update — 2026 Families

1. **Qwen3.5-9B** — primary quality/speed candidate. Apache-2.0, February 2026, native image-text Transformers path, 9B language model, strong official vision benchmark profile. Thinking must be disabled and output length capped for the 70-minute requirement.
2. **GLM-4.6V-Flash** — architecture-diverse 9B candidate. MIT, native processor/chat template, BF16 checkpoint approximately 20.6GB, explicitly positioned for local low-latency deployment. Main risk is the recent Transformers/vLLM dependency floor.
3. **MiniCPM-o-4.5** — architecture-diverse 9B candidate. Apache-2.0, public before the cutoff, strong official vision claims, INT4/vLLM/SGLang support. Main risk is custom remote code and model-specific chat behavior.
4. **Qwen3.5-4B** — speed-insurance candidate. Same native integration and license as 9B, with official vision scores often close to the 9B variant. Use if 9B misses A6000 runtime.
5. **Qwen2.5-VL-7B-Instruct** — known reproducible baseline, not the expected quality winner. It anchors prompt and score changes against the existing measured path.

Reserve: Kimi-VL-A3B-Instruct and InternVL3.5-8B. Exclude Qwen3.6-27B two-pass from the final-eligible shortlist until it proves A6000 Test ≤70 minutes and Hidden ≤13 minutes.

Sources: [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B), [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B), [GLM-4.6V-Flash](https://huggingface.co/zai-org/GLM-4.6V-Flash), [MiniCPM-o-4.5](https://huggingface.co/openbmb/MiniCPM-o-4_5), [Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)
