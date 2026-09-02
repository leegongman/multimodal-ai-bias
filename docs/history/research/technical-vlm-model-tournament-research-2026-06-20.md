---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/history/research/technical-multimodal-236722-1-vlm-model-candidate-research-2026-06-19.md
  - experiments/investigations/submission-score-091-investigation.md
  - _bmad-output/specs/spec-reasoner-v3-contract/SPEC.md
  - _bmad-output/specs/spec-shadow-private-validation/SPEC.md
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Multimodal 236722 VLM 모델 tournament 및 최종 후보 선정'
research_goals: '공개 가중치 cutoff, license, 정확한 revision, offline 재현성, RTX A6000 48GB VRAM/runtime, Reasoner-only 성능, Verifier 역할, Transformers/vLLM 실행 경로를 검증하여 실행 가능한 shortlist, 제외 목록, 단계별 tournament matrix와 promotion gate를 확정한다.'
user_name: 'gongman'
date: '2026-06-20'
web_research_enabled: true
source_verification: true
operator_notification_required: true
---

# Multimodal 236722 VLM 모델 Tournament: 재현 가능한 Private-Generalization 기술 조사

**Date:** 2026-06-20
**Author:** gongman
**Research Type:** technical

---

## Research Overview

이 조사는 첫 Qwen2.5-VL-7B 제출의 Public 0.91 결과만으로 모델과 프롬프트의 책임을 단정하지 않고, Reasoner 의미 계약·독립 Shadow Private·모델 tournament·Verifier·A6000 실행 가능성을 분리해 검증하기 위해 수행했다. 공식 Multimodal 규칙, 모델 카드, Transformers/vLLM/PyTorch 문서와 현재 프로젝트 구현을 교차 검토했다.

핵심 결론은 모델 교체가 첫 단계가 아니라는 것이다. 먼저 Reasoner v3의 선택지 인덱스 계약을 구현하고 300~600건 Shadow Private를 동결한 뒤, 동일 Qwen에서 v2/v3를 비교해야 한다. 이후 Qwen 7B corrected control, MiniCPM-V 4.5, LLaVA-OneVision 7B, InternVL3-14B와 조건부 Qwen 32B-AWQ를 단계적으로 평가한다. 최종 판단과 실행 순서는 아래 `Research Synthesis`에 정리했다.

## Table of Contents

1. Technical Research Scope Confirmation
2. Operator Notification Gate
3. Technology Stack Analysis
4. Integration Patterns Analysis
5. Architectural Patterns and Design
6. Implementation Approaches and Technology Adoption
7. Technical Research Recommendations
8. Research Synthesis

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** Multimodal 236722 VLM 모델 tournament 및 최종 후보 선정

**Research Goals:** 공개 가중치 cutoff, license, 정확한 revision, offline 재현성, RTX A6000 48GB VRAM/runtime, Reasoner-only 성능, Verifier 역할, Transformers/vLLM 실행 경로를 검증하여 실행 가능한 shortlist, 제외 목록, 단계별 tournament matrix와 promotion gate를 확정한다.

**Technical Research Scope:**

- Architecture Analysis - Reasoner/Verifier 역할, local inference 및 artifact 경계
- Implementation Approaches - 모델 adapter, structured output, offline snapshot 재현성
- Technology Stack - PyTorch, Transformers, vLLM과 후보별 공식 실행 경로
- Integration Patterns - in-process와 self-managed local serving 비교
- Performance Considerations - A6000 48GB VRAM, throughput, 전체 8,500건 runtime

**Research Methodology:**

- 현재 공식 웹 자료와 모델 카드 기반 검증
- 공개일, license, revision 및 engine 지원의 다중 출처 확인
- 불확실한 적합성에 confidence level 부여
- 동일 Shadow Private와 고정 조건을 사용하는 tournament 설계

**Scope Confirmed:** 2026-06-20

## Operator Notification Gate

GPU 환경에서 모델 snapshot, prompt/schema, data path, dependency, smoke inference, runtime projection과 submission validation 조건이 충족되어 유효한 `submission.csv` 산출이 가능해지는 즉시 사용자에게 알린다. 알림 전에는 8,500건 production inference를 준비 완료로 간주하지 않는다.

## Technology Stack Analysis

### Programming Languages

평가 실행 언어는 Python이며 프로젝트와 운영진 기준 환경은 Python 3.10으로 고정한다. 후보 모델이 최신이어도 Python 3.10에서 설치·로드·추론·submission 생성이 모두 재현되어야 한다. 모델별 샘플 코드가 최신 Python만 전제하면 tournament 진입 전에 제외하거나 호환 환경을 별도 고정한다.

_Primary Language:_ Python 3.10  
_Performance Boundary:_ CUDA kernel과 model runtime은 PyTorch/vLLM이 담당하고 application orchestration은 Python package/CLI가 담당한다.  
_Source:_ [Multimodal 평가 규칙 안내](공식 원문 링크 제외)

### Development Frameworks and Libraries

기준 stack은 PyTorch 2.6.0 + CUDA 12.4, Hugging Face Transformers, Pillow/processor 계층이다. PyTorch 공식 이전 버전 문서는 `torch==2.6.0`, `torchvision==0.21.0`, `torchaudio==2.6.0`의 CUDA 12.4 wheel 설치 경로를 제공한다. Transformers는 `HF_HUB_OFFLINE=1`과 `local_files_only=True`를 제공하므로 model, processor, tokenizer와 custom code를 snapshot에 고정하는 in-process baseline에 적합하다.

vLLM은 Qwen·InternVL 등 여러 multimodal architecture를 지원하며 continuous batching과 local serving 후보가 된다. 다만 tournament에서는 Transformers와 logical prompt, image bytes/hash, decoding, output schema가 동일한지 확인한 뒤 속도 최적화 단계에서만 비교한다. 외부 managed inference API는 금지하며 self-managed local server도 최종 검증 구조와 dependency를 모두 기록해야 한다.

_Baseline Framework:_ Transformers in-process local inference  
_Optimization Candidate:_ vLLM local engine after output-equivalence gate  
_Source:_ [PyTorch previous versions](https://pytorch.org/get-started/previous-versions/), [Transformers offline mode](https://huggingface.co/docs/transformers/v4.49.0/en/installation), [vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models.html)

### Candidate Model Framework Fit

| 후보 | 공식 local 경로 | 라이선스 신호 | 현재 stack 영향 | 기술 스택 판정 |
|---|---|---|---|---|
| Qwen2.5-VL-7B-Instruct | Transformers image-text-to-text, vLLM 지원 계열 | Apache-2.0 | 기존 `hf_local` adapter와 config 존재 | 기준선 유지 |
| LLaVA-OneVision Qwen2 7B | Transformers image-text-to-text | Apache-2.0 | baseline 계열, adapter smoke 필요 | 저위험 대조군 |
| InternVL3-14B | `AutoModel` + `trust_remote_code=True`; vLLM/LMDeploy 계열 | model card상 MIT, Qwen2.5 component Apache-2.0 | 별도 adapter 또는 HF-format 검증, 약 30GB weight snapshot | 성능 shortlist 후보, GPU smoke 필수 |
| MiniCPM-V 4.5 | `AutoModel`/`AutoTokenizer` + `model.chat`, `trust_remote_code=True` | HF card상 Apache-2.0 | 전용 adapter가 이미 있으나 exact revision/custom code audit 필요 | 효율 shortlist 후보, cutoff·GPU smoke 필수 |
| Qwen2.5-VL-32B-Instruct/AWQ | 공식 Transformers model 및 AWQ repo | Apache-2.0 | BF16은 단일 48GB에 부적합할 가능성이 높아 공식 양자화 경로 필요 | 양자화 성능 후보로만 유지 |

이 표는 tournament 확정 순위가 아니다. exact repository creation/weight publication date, immutable commit, license file, A6000 peak VRAM/runtime과 Shadow Private 결과를 모두 통과해야 shortlist가 확정된다.

_Source:_ [Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [Qwen2.5-VL-32B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct), [Qwen2.5-VL-32B-Instruct-AWQ](https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct-AWQ), [LLaVA-OneVision 7B](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-hf), [InternVL3-14B](https://huggingface.co/OpenGVLab/InternVL3-14B), [MiniCPM-V 4.5](https://huggingface.co/openbmb/MiniCPM-V-4_5)

### Database and Storage Technologies

데이터베이스는 필요하지 않다. official data와 model snapshot은 read-only local storage, run 결과는 immutable directory와 JSONL/CSV/YAML/JSON artifact로 관리한다. GPU tournament에서는 model snapshot commit/hash, prompt hash, image hash, environment lock, raw output과 metric을 한 run directory에 묶어 후보 간 재현성을 유지한다.

_Relational/NoSQL Database:_ 사용하지 않음  
_Required Storage:_ persistent local/network volume + immutable run artifacts  
_Reason:_ Pod 삭제와 partial output 손실을 방지하고 offline 재현성을 증명한다.

### Development Tools and Platforms

`uv`가 Python/dependency lock과 CLI 실행을 담당하고 `pytest`/Ruff가 CPU contract를 검증한다. GPU 후보는 별도 smoke command, diagnostic-48, Shadow Private, projected/full runtime 순서로 승격한다. Hugging Face snapshot은 tournament 전에 다운로드하고 exact commit을 기록하며 production inference에서는 network를 차단한다.

_Build/Environment:_ `uv`, Python 3.10, pinned GPU requirements  
_CPU QA:_ pytest, Ruff, schema/artifact tests  
_GPU QA:_ load smoke, one-image structured-output smoke, diagnostic-48, Shadow Private, runtime benchmark  
_Source:_ [Transformers offline mode](https://huggingface.co/docs/transformers/v4.49.0/en/installation)

### Cloud Infrastructure and Deployment

RunPod 같은 참가자 관리 GPU VM은 model weights를 직접 로드하는 범위에서 사용한다. OpenAI, Gemini, Hugging Face Inference API, Together, OpenRouter 등 외부 model-response API는 금지된다. 최종 candidate는 RTX A6000 48GB 한 장에서 offline 재현되어야 하며 H100/A100에서만 성공한 결과는 promotion 근거가 될 수 없다.

_Primary Target:_ single RTX A6000 48GB  
_Cloud Role:_ self-managed GPU machine, not managed inference API  
_Source:_ [Multimodal 평가 규칙 안내](공식 원문 링크 제외)

### Technology Adoption Trends

공식 모델 카드와 vLLM 문서는 multimodal Transformers pipeline과 local high-throughput engine 지원이 확대되고 있음을 보여준다. 그러나 최신 engine 지원 자체는 평가 적격성이나 정확도를 보장하지 않는다. 이 프로젝트에서는 새 모델·engine 채택 순서를 `cutoff/license → offline load → A6000 fit → structured output → Shadow Private → runtime → Public sanity`로 고정한다.

_Stable Path:_ Qwen2.5-VL-7B + Transformers는 이미 실행된 기준선이다.  
_Near-term Candidates:_ LLaVA-OneVision 7B, MiniCPM-V 4.5, InternVL3-14B.  
_Conditional Candidate:_ Qwen2.5-VL-32B AWQ는 양자화 품질과 runtime을 통과할 때만 유지한다.  
_Deferred:_ cutoff·license·exact revision 또는 A6000 feasibility가 입증되지 않은 최신 모델.

## Integration Patterns Analysis

### API Design Patterns

후보 모델 공통 경계는 network API가 아니라 typed Python adapter다. Canonical request는 original image bytes, system intent, user task, ordered answer choices, decoding config와 audit identity를 가진다. 각 adapter는 이 logical request를 모델 고유 chat template과 image processor로 직렬화하고 raw generated text와 preprocessing/generation metadata를 반환한다.

Qwen2.5-VL은 `AutoProcessor.apply_chat_template`, `process_vision_info`, processor, `model.generate` 순서를 공식 예제로 사용한다. LLaVA-OneVision도 processor chat template과 `AutoModelForImageTextToText` 경로를 제공한다. MiniCPM-V 4.5는 `AutoModel`/`AutoTokenizer`와 `model.chat`, InternVL3는 custom model code, dynamic image tiling과 chat 경로를 사용한다. 따라서 하나의 generic string-only adapter로 네 모델을 동일하다고 간주하면 이미지 전처리와 control token 차이가 성능 confounder가 된다.

_RESTful APIs:_ 외부/managed model API는 금지. self-managed vLLM HTTP는 throughput 실험 후보지만 최종 구조의 우선안은 아님.  
_In-process API:_ tournament 기준 경계. Transformers 또는 vLLM Python API를 typed adapter 뒤에서 사용.  
_GraphQL/RPC/Webhook:_ 적용하지 않음.  
_Source:_ [Qwen2.5-VL official model card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [MiniCPM-V 4.5 official model card](https://huggingface.co/openbmb/MiniCPM-V-4_5), [InternVL3-14B official model card](https://huggingface.co/OpenGVLab/InternVL3-14B), [LLaVA-OneVision chat HF model](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-chat-hf)

### Communication Protocols

프로세스 내부 통신은 Python typed records이며 stage 간 영속 통신은 local artifact다. vLLM을 사용할 경우에도 loopback-only local process 또는 in-process `LLM` 경계를 사용하고 request가 외부 network로 나가지 않음을 audit한다. GPU production에서는 image URL을 사용하지 않고 검증된 local bytes/path만 전달한다.

_HTTP/HTTPS:_ model snapshot 사전 다운로드에만 사용; production inference 중 외부 통신 금지.  
_Loopback HTTP:_ vLLM engine A/B에서만 조건부 허용하고 host/port/process/version을 기록.  
_WebSocket/Message Queue/gRPC:_ 불필요.  
_Source:_ [Multimodal 평가 규칙 안내](공식 원문 링크 제외), [vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models.html)

### Data Formats and Standards

Canonical logical request와 model-specific rendered request를 분리해 기록한다.

- `logical_prompt_text`와 SHA-256: 모델 간 동일해야 하는 task contract
- `rendered_prompt_text` 또는 rendered token/input fingerprint: model/engine별 chat template 결과
- `image_sha256`, decoded width/height, processor pixel budget, tile/grid 정보
- model repo id, immutable revision, adapter/engine/version, dtype/quantization
- raw generated text, schema version, parsed record와 failure status

Reasoner v3와 Verifier v2 output은 strict JSON marker를 사용하지만 raw text를 먼저 보존한다. JSON schema validation은 syntax와 semantic consistency를 검사할 뿐 label을 매핑하거나 발명하지 않는다.

_JSON/JSONL:_ raw request/response와 per-sample audit  
_CSV:_ parsed/final predictions와 official submission  
_YAML/JSON:_ resolved prompt/model/run config와 manifest  
_Binary formats:_ model safetensors와 local image bytes; artifact에는 hash/metadata만 기록  
_Source:_ [Transformers multimodal chat templates](https://huggingface.co/docs/transformers/chat_templating_multimodal), [Hugging Face snapshot download](https://huggingface.co/docs/huggingface_hub/en/guides/download)

### System Interoperability Approaches

`VisionLanguageModelAdapter`는 model-specific implementation을 숨기되 입력 변환을 숨겨서 감사 불가능하게 만들면 안 된다. 공통 result에는 최소 raw text, elapsed time, model load metadata, rendered-input fingerprint와 image preprocessing metadata가 포함돼야 한다.

| 후보 | required serialization | integration risk |
|---|---|---|
| Qwen2.5-VL | processor chat template + Qwen vision preprocessing | Low: 현재 HF adapter 존재, pixel metadata 보강 필요 |
| LLaVA-OneVision | processor multimodal chat template | Low-Medium: model class/chat template smoke 필요 |
| MiniCPM-V 4.5 | PIL image + prompt in `model.chat`; thinking mode 통제 | Medium: custom code와 generation args audit 필요 |
| InternVL3-14B | dynamic tiles + tokenizer/model chat | Medium-High: tiling `max_num`, custom code, 별도 adapter 필요 |
| vLLM engine variants | engine-supported multimodal message format | Medium: rendered input/output equivalence와 local process 재현 필요 |

_Point-to-Point:_ CLI → adapter → immutable run artifacts가 기본.  
_API Gateway/Service Mesh/ESB:_ 적용하지 않음.  
_Source:_ [Transformers multimodal chat templates](https://huggingface.co/docs/transformers/chat_templating_multimodal), [InternVL3-14B Quick Start](https://huggingface.co/OpenGVLab/InternVL3-14B)

### Engine Equivalence Gate

Transformers와 vLLM 비교는 단순 label 일치율이 아니라 다음을 고정·검사한다.

1. 동일 model snapshot revision과 quantization.
2. 동일 logical message, ordered choices, original image hash.
3. 동일 do-sample/temperature/max-new-tokens/stop 조건.
4. engine별 rendered prompt, image budget/grid/tile metadata 기록.
5. diagnostic-48에서 parse success, label/raw difference, latency, VRAM 비교.
6. 차이가 있으면 engine을 속도 대체재로 간주하지 않고 별도 candidate로 평가.

Chat template의 control token이 모델마다 다르면 성능이 크게 달라질 수 있으므로 공식 processor/template를 우회하지 않는다.

_Source:_ [Transformers chat templates](https://huggingface.co/docs/transformers/en/chat_templating), [Writing multimodal chat templates](https://huggingface.co/docs/transformers/chat_templating_writing)

### Reasoner and Verifier Interoperability

Verifier는 원본 image/context/question/answers와 Reasoner v3의 raw/parsed output을 받는다. Reasoner가 생성한 `uncertainty_option_index`를 참고 정보로 보되 Verifier는 자신의 label과 uncertainty index를 독립적으로 생성한다. arbitration은 두 generated candidates와 evidence metadata만 비교하며 trigger 또는 숫자 label에서 답을 생성하지 않는다.

Verifier model 조합은 adapter 독립성을 유지한다.

- same-model: Reasoner와 동일 snapshot, 별도 verifier prompt
- stronger-verifier: 상위 성능 모델을 triggered subset에만 사용
- reasoner-only: verifier 효과를 판단하는 필수 control

각 조합은 별도 run candidate이며 majority vote로 합치지 않는다.

### Microservices Integration Patterns

microservice, service discovery, gateway, saga는 필요하지 않다. vLLM server를 사용하더라도 이는 하나의 GPU batch engine process이며 분산 서비스 architecture로 확장하지 않는다. per-sample failure는 queue retry가 아니라 immutable status와 명시적 rerun policy로 관리한다.

_Circuit Breaker Equivalent:_ model load/run-level failure는 candidate 중단; recoverable sample failure는 artifact에 기록하고 submission gate에서 unresolved를 차단.  
_Other Microservice Patterns:_ 적용하지 않음.

### Event-Driven Integration

event broker는 사용하지 않는다. ordered batch iteration, durable partial JSONL, atomic final publication이 요구사항에 더 적합하다. 중단 복구가 추가될 경우에도 completed sample artifact를 명시적으로 읽는 resume command로 구현하며 hidden queue state를 두지 않는다.

_Publish-Subscribe/Event Sourcing/Message Broker/CQRS:_ 적용하지 않음.

### Integration Security Patterns

모든 snapshot은 exact commit으로 사전 다운로드하고 custom code를 포함해 hash/라이선스를 기록한다. production은 `HF_HUB_OFFLINE=1`, `local_files_only=True`와 network-disabled smoke를 통과해야 한다. `trust_remote_code=True` 후보는 snapshot 내부 code가 실행 대상이므로 model weights와 동일한 compliance artifact로 취급한다.

image loader는 URL fetch를 금지하고 local verified bytes만 adapter에 전달한다. prompt/raw output에 API token이나 credential이 없어야 한다.

_OAuth/JWT/API Keys/mTLS:_ production inference에 사용하지 않음.  
_Integrity:_ snapshot, prompt, image, environment와 artifacts의 SHA-256 기록.  
_Offline Enforcement:_ offline environment variables + local-only load + network-disabled smoke.  
_Source:_ [Transformers offline mode](https://huggingface.co/docs/transformers/v4.49.0/en/installation), [Hugging Face snapshot revisions](https://huggingface.co/docs/huggingface_hub/en/guides/download)

## Architectural Patterns and Design

### System Architecture Patterns

선택 architecture는 modular monolith CLI + model adapter plugin + immutable run artifact 구조다. 별도 서비스나 database 없이 각 tournament stage가 이전 stage의 signed manifest를 입력으로 받아 새 run artifact를 만든다. 모델 비교와 submission 생성은 동일 package 경계 안에서 실행되며 final label은 generated text parsing과 arbitration을 통해서만 이동한다.

Tournament는 다음 funnel을 따른다.

1. **Eligibility Gate:** cutoff, official weights, license, immutable revision, offline snapshot.
2. **Integration Gate:** A6000 load, original image 전달, official chat template, Reasoner v3 valid JSON.
3. **Diagnostic Gate:** 독립 48건으로 label mapping, image omission, pixel/tiling, engine 차이 분리.
4. **Reasoner Selection Gate:** Shadow Private selection split에서 Reasoner-only 후보 비교.
5. **Sealed Shortlist Gate:** 상위 후보만 sealed holdout aggregate metric 평가.
6. **Verifier Gate:** shortlist에 reasoner-only, same-model verifier, stronger-verifier를 별도 run으로 비교.
7. **Runtime/Compliance Gate:** full path의 A6000 VRAM, end-to-end runtime, offline audit.
8. **Submission Portfolio Gate:** local gate를 통과한 상위 2~3개만 Public sanity submission 후보로 지정.

이 구조는 약한 Reasoner에 Verifier를 먼저 붙여 비용과 오류 원인을 섞는 것을 방지한다.

_Pattern:_ staged evaluation pipeline with fail-closed promotion  
_Trade-off:_ 실험 횟수는 늘지만 원인 분리와 Private 일반화 판단력이 높아진다.  
_Source:_ [Multimodal 평가 규칙 안내](공식 원문 링크 제외), [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html)

### Candidate Architecture and Initial Status

| candidate id | model path | initial role | architecture status |
|---|---|---|---|
| `qwen25vl7b_bf16_hf` | Qwen2.5-VL-7B-Instruct | 현재 0.91 run의 corrected baseline | Gate 1 진입 가능; exact revision 보완 필요 |
| `llavaov7b_bf16_hf` | LLaVA-OneVision Qwen2 7B Chat | 저위험 architecture comparator | adapter/config 및 A6000 smoke 필요 |
| `minicpmv45_bf16_hf` | MiniCPM-V 4.5 | 효율·OCR 성능 후보 | existing adapter review, exact revision, custom code audit 필요 |
| `internvl3_14b_bf16_hf` | InternVL3-14B | 중형 성능 후보 | dynamic tiling adapter, A6000 VRAM/runtime smoke 필요 |
| `qwen25vl32b_awq` | Qwen2.5-VL-32B-Instruct-AWQ | 대형 양자화 성능 후보 | official quantized snapshot, vLLM/HF support와 품질 gate 통과 시에만 유지 |

공식 공개 시점 신호는 Qwen2.5-VL 3B/7B/72B가 2025-01-26, Qwen2.5-VL-32B가 2025-03-24, InternVL3 family가 2025-04-11, LLaVA-OneVision이 2024-08에 공개되어 cutoff 이전이다. MiniCPM-V 4.5도 공식 model card/paper가 2025-09를 가리키지만 exact weight repository history와 commit을 Eligibility Gate에서 다시 고정한다.

_Source:_ [Qwen2.5-VL release](https://qwenlm.github.io/blog/qwen2.5-vl/), [Qwen2.5-VL-32B release](https://qwenlm.github.io/blog/qwen2.5-vl-32b/), [InternVL3 release](https://internvl.github.io/blog/2025-04-11-InternVL-3.0/), [LLaVA-OneVision release](https://llava-vl.github.io/blog/2024-08-05-llava-onevision/), [MiniCPM-V 4.5 model card](https://huggingface.co/openbmb/MiniCPM-V-4_5)

### Design Principles and Best Practices

- **One variable per diagnostic A/B:** prompt contract, model, image budget, engine, Verifier를 동시에 바꾸지 않는다.
- **Generated-candidate lineage:** parser, trigger, Verifier, arbitration이 label을 발명하지 않는다.
- **Fail closed:** invalid/unresolved, missing artifact, revision/license 미확정, runtime 초과는 promotion과 submission을 차단한다.
- **Official serialization:** 각 model의 processor/chat template와 image pipeline을 사용하고 rendered input을 감사한다.
- **Immutable comparison:** dataset, model, prompt, engine, metric version을 hash로 묶는다.
- **Selection/holdout separation:** tuning 가능한 selection 결과와 sealed aggregate 결과를 분리한다.
- **Public is secondary:** Public score는 local gate 통과 후보의 sanity signal이다.

PyTorch는 release/platform 간 완전한 재현성을 보장하지 않으므로 seed뿐 아니라 exact software/hardware와 raw output을 기록한다.

_Source:_ [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html), [Transformers chat templates](https://huggingface.co/docs/transformers/en/chat_templating)

### Scalability and Performance Patterns

single A6000 48GB가 fixed target이다. NVIDIA 공식 사양은 RTX A6000에 48GB GDDR6 ECC를 명시한다. 후보는 model load 성공뿐 아니라 image tokens, KV cache, generation workspace와 batch/concurrency를 포함한 peak VRAM으로 평가한다.

- Transformers baseline: deterministic ordered batching 또는 small batch; processor와 generation 시간을 분리 기록.
- vLLM candidate: offline batch inference와 continuous batching을 사용하되 engine-equivalence gate 필요.
- larger models: `device_map="auto"` load 성공은 performance 합격이 아니다. Accelerate는 GPU 이후 CPU/disk offload를 사용할 수 있고 이 경로는 overhead가 있으므로 production candidate는 실제 device map과 runtime을 기록한다.
- quantized candidates: BF16 candidate와 별도 model candidate로 취급하고 accuracy 회귀를 Shadow Private에서 측정한다.
- Verifier: trigger rate를 포함한 end-to-end 8,500건 projection으로 평가한다.

_Capacity Gate:_ peak VRAM이 실제 A6000 여유 내에 있고 startup + Reasoner + selected Verifier + artifact/submission 시간이 70분 내여야 한다.  
_Source:_ [NVIDIA RTX A6000 specification](https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/quadro-product-literature/proviz-print-nvidia-rtx-a6000-datasheet-us-nvidia-1454980-r9-web%20%281%29.pdf), [Accelerate big model inference](https://huggingface.co/docs/accelerate/v1.6.0/usage_guides/big_modeling), [vLLM offline inference](https://docs.vllm.ai/en/latest/serving/offline_inference.html)

### Integration and Communication Patterns

CLI command가 stage boundary다. 각 stage는 explicit input manifest를 읽고 새 immutable output을 atomic publish한다.

```text
eligibility manifest
  -> GPU smoke artifact
  -> diagnostic report
  -> selection metrics
  -> sealed aggregate report
  -> verifier comparison
  -> runtime/compliance report
  -> promotion rationale
  -> submission.csv
```

stage 간 암묵적 global state, latest-file 추측, position-only join을 금지한다. `run_id`, ordered `sample_id`, schema version과 artifact hash를 검증한다.

_Source:_ [Hugging Face snapshot revisions](https://huggingface.co/docs/huggingface_hub/en/guides/download)

### Security Architecture Patterns

final execution은 network-disabled local inference다. Model snapshot은 immutable commit으로 준비하고 `trust_remote_code=True` code를 audit manifest에 포함한다. raw data는 read-only, run artifacts는 no-overwrite, submission은 validated final predictions만 소비한다.

Eligibility manifest 필수 항목:

- official repo와 exact commit
- first public weight evidence before cutoff
- license file/hash와 component license
- custom code file manifest
- remote API usage `none`
- external validation data provenance

_Source:_ [Transformers offline mode](https://huggingface.co/docs/transformers/v4.49.0/en/installation), [Multimodal 평가 규칙 안내](공식 원문 링크 제외)

### Data Architecture Patterns

Shadow Private suite는 versioned manifest와 split hash를 갖는 read-only input이다. Candidate run은 raw output, parsed output, per-subset metrics, uncertainty-position metrics, latency/VRAM과 compliance를 함께 보존한다. Sealed holdout의 sample-level 결과는 final shortlist 결정 전 prompt 작성자에게 노출하지 않는다.

Run comparison은 metric JSON을 읽어 표를 만들되 missing metric을 0으로 대체하지 않고 candidate를 incomplete로 표시한다. Dataset version이 다른 run은 동일 tournament ranking에 직접 비교하지 않는다.

### Deployment and Operations Architecture

GPU deployment는 persistent volume에 project, model snapshots와 runs를 두는 단일-machine batch job이다. Production 전에 다음 readiness checklist를 모두 통과한다.

1. RTX A6000 48GB와 driver/CUDA/PyTorch version 확인.
2. exact model snapshot/revision/license manifest와 offline load 성공.
3. official data path/image validation 성공.
4. Reasoner v3 및 선택된 Verifier prompt/schema hash 고정.
5. 실제 local image를 사용한 valid structured-output smoke 성공.
6. diagnostic subset에서 parse/image/unresolved blocking failure 0.
7. selected engine의 peak VRAM과 end-to-end 8,500건 projection이 70분 이내.
8. persistent partial/final artifact와 atomic publication 확인.
9. fixture 또는 candidate artifact에서 final prediction/submission validation 성공.
10. network-disabled rerun smoke 성공.

10개가 충족되는 순간 `GPU_SUBMISSION_READY`로 기록하고 8,500건 production inference 전에 사용자에게 알린다. 하나라도 실패하면 준비 완료 알림을 하지 않는다.

_Operations Pattern:_ preflight → explicit user notification → production run → artifact verification → upload handoff.  
_Source:_ [PyTorch 2.6 CUDA 12.4 installation](https://pytorch.org/get-started/previous-versions/), [Transformers offline mode](https://huggingface.co/docs/transformers/v4.49.0/en/installation)

## Implementation Approaches and Technology Adoption

### Technology Adoption Strategies

채택 방식은 big-bang 교체가 아니라 현재 Qwen2.5-VL-7B Transformers 경로를 control로 유지하는 단계적 funnel이다. Reasoner v3와 Shadow Private 계약을 먼저 구현하고, 이후 모델·engine·Verifier를 한 번에 하나씩 변경한다. 후보는 `eligibility → adapter smoke → diagnostic-48 → selection → sealed holdout → runtime/compliance` 순으로 승격한다.

모델 snapshot은 repository 이름만 기록하지 않고 exact commit으로 다운로드한다. Hugging Face `snapshot_download()`와 `hf download`는 revision 지정과 snapshot 단위 다운로드를 지원하므로 commit, license, custom code manifest와 파일 hash를 eligibility artifact에 고정한다. production에서는 이미 준비된 snapshot만 `local_files_only=True`로 읽는다.

_Source:_ [Hugging Face snapshot download](https://huggingface.co/docs/huggingface_hub/en/guides/download), [Transformers offline mode](https://huggingface.co/docs/transformers/v4.49.0/en/installation)

### Development Workflows and Tooling

공통 application package와 candidate-specific GPU environment를 분리한다. core schema, prompt, parsing, validation, comparison과 submission은 현재 `src/multimodal_bias`에 유지하고 model adapter/config/requirements만 후보별로 격리한다. 기존 `hf_local` adapter는 Qwen과 LLaVA의 1차 integration 경로로 사용하고, MiniCPM은 현재 `minicpm_v`, InternVL은 dynamic tiling과 `model.chat`을 캡슐화한 별도 adapter를 추가한다.

| candidate | 우선 구현 경로 | 환경/adapter 결정 |
|---|---|---|
| Qwen2.5-VL-7B | 현재 `hf_local` + official processor template | corrected baseline; exact revision과 pixel metadata 보강 |
| LLaVA-OneVision-7B | `hf_local` 또는 얇은 LLaVA specialization | Transformers 4.45+ model class와 image/chat smoke |
| MiniCPM-V-4.5 | 기존 `minicpm_v` | `enable_thinking=False`, generation args, custom code hash 감사 |
| InternVL3-14B | 새 `internvl_v` | official dynamic tiling/max_num, AutoTokenizer/AutoModel chat 경로 |
| Qwen2.5-VL-32B-AWQ | 별도 AWQ environment | dependency/engine 충돌과 accuracy 회귀 통과 시에만 유지 |

Transformers multimodal chat은 processor가 chat template, image preprocessing와 tokenization을 함께 처리하고 `pixel_values`와 grid/size metadata를 생성한다. 따라서 logical request는 공통화하되 serialization은 각 공식 processor/adapter에 맡긴다. AWQ는 AutoAWQ 설치가 Transformers version을 변경할 수 있다는 공식 경고가 있으므로 baseline environment에 혼합하지 않는다.

`uv.lock`과 candidate requirements/lock evidence를 함께 보존하고 production command는 locked/frozen dependency로 실행한다. uv는 lockfile과 project metadata 불일치 시 `--locked` 실행을 실패시킬 수 있어 silent dependency upgrade를 방지할 수 있다.

_Source:_ [Transformers multimodal chat templates](https://huggingface.co/docs/transformers/chat_templating_multimodal), [LLaVA-OneVision 7B model card](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-chat-hf), [InternVL3-14B model card](https://huggingface.co/OpenGVLab/InternVL3-14B), [MiniCPM-V 4.5 model card](https://huggingface.co/openbmb/MiniCPM-V-4_5), [Transformers AWQ](https://huggingface.co/docs/transformers/main/quantization/awq), [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)

### Testing and Quality Assurance

테스트는 CPU contract와 GPU evidence로 분리한다.

1. **CPU unit/contract:** uncertainty option index 0/1/2 parameterization, semantic invariant, invalid JSON, unresolved fail-closed, adapter request serialization, artifact hash와 submission guards.
2. **Golden adapter fixtures:** fake processor/model로 image block, ordered choices, rendered prompt, generated suffix trimming과 metadata를 검사한다.
3. **Real-image GPU smoke:** 후보별 exact snapshot으로 동일한 local image를 읽고 image tensor/grid가 존재하며 Reasoner v3 JSON이 valid한지 확인한다.
4. **Diagnostic-48:** mapping, image omission, resolution, template와 engine equivalence를 promotion corpus와 분리해 검사한다.
5. **Shadow Private:** selection은 상세 분석, sealed holdout은 shortlist 확정 전 aggregate-only로 사용한다.
6. **Runtime QA:** warmup과 timed run을 구분하고 average/p95, throughput, peak allocated/reserved VRAM, startup과 artifact 시간을 기록한다.

PyTorch `max_memory_allocated()`는 reset 이후 tensor가 차지한 peak GPU memory를 제공한다. 이 값만으로 process 전체 VRAM을 설명할 수 없으므로 NVML/nvidia-smi process memory도 함께 기록한다. vLLM benchmark를 사용할 경우 실제 image rendering 비용을 포함하고 multimodal preprocessing과 scheduling overlap을 명시한다.

_Source:_ [PyTorch max_memory_allocated](https://docs.pytorch.org/docs/stable/generated/torch.cuda.max_memory_allocated.html), [vLLM throughput benchmark](https://docs.vllm.ai/en/latest/cli/bench/throughput/), [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html)

### Deployment and Operations Practices

RunPod/A6000 배포는 persistent volume의 project, exact model snapshots, datasets와 run artifacts를 사용하는 단일-machine batch job으로 운영한다. 외부 model-response API는 사용하지 않고 model weights를 직접 로드한다. Multimodal 기준 환경에서 package version 조정은 가능하지만 RTX A6000 48GB, Python 3.10, CUDA 12.4, PyTorch 2.6.0, Ubuntu 20.04에서 최종 경로가 재현돼야 한다.

배포 절차는 `environment preflight → offline model load → one-image structured smoke → diagnostic → Shadow Private/runtime → GPU_SUBMISSION_READY notification → 8,500 production → submission audit`이다. 전체 70분 기준에 startup과 최종 CSV publication도 포함하고 내부 운영 목표는 약 10% 여유를 둔 63분 이하로 둔다.

partial JSONL은 persistent storage에 atomic하게 갱신하고 final artifacts는 모든 row와 schema/hash 검증 후 publish한다. 유효한 generated candidate가 없는 sample, 누락 artifact, revision/license 불명 또는 runtime gate 실패는 submission 생성을 차단한다.

_Source:_ [Multimodal 평가 규칙 안내](공식 원문 링크 제외), [vLLM offline inference](https://docs.vllm.ai/en/latest/serving/offline_inference/)

### Team Organization and Skills

작은 팀/단일 운영자 기준으로 역할을 artifact gate로 분리한다.

- **Contract owner:** Reasoner v3, Verifier, arbitration semantic invariant와 leakage 금지 검토.
- **Data reviewer:** Shadow Private provenance, label, subset과 sealed split을 검수하고 prompt 작업자에게 holdout sample detail을 노출하지 않는다.
- **Model integrator:** official adapter, exact snapshot, dependency와 A6000 smoke를 담당한다.
- **Evaluation owner:** metric/comparison/promotion report를 생성하고 Public score를 secondary signal로만 기록한다.
- **Operator/reviewer:** GPU readiness, runtime, compliance와 submission artifact를 승인한다.

한 사람이 여러 역할을 수행하더라도 같은 session에서 dataset label 작성과 sealed error inspection, prompt 수정과 promotion 승인을 연속 수행하지 않고 manifest와 review checkpoint를 남긴다.

### Cost Optimization and Resource Management

비용 최적화의 핵심은 작은 gate에서 조기 탈락시키는 것이다. exact eligibility/CPU tests는 GPU 없이 수행하고, GPU는 1건 smoke → diagnostic-48 → selection → sealed shortlist 순으로 확장한다. InternVL3-14B와 Qwen32-AWQ는 Qwen/LLaVA/MiniCPM 저비용 후보의 기준을 통과한 뒤에만 실행한다.

Verifier는 전건 실행하지 않고 reasoner-only control과 trigger rate를 먼저 측정한다. end-to-end projection은 Reasoner 시간뿐 아니라 `trigger_rate × verifier latency`, model startup, parsing, persistence와 submission generation을 포함한다. 빠른 engine 전환은 quality equivalence 이후에만 수행한다.

### Risk Assessment and Mitigation

| 위험 | 영향 | 완화/차단 조건 |
|---|---|---|
| Reasoner v3가 backlog에 없는 상태로 Epic 3 구현 | 고정 label 의미 재발 | 명시적 corrective story와 0/1/2 contract tests 선행 |
| Shadow Private가 schema만 있고 실제 corpus가 없음 | 모델 선택 근거 부재 | 300~600건 구축·이중 검수·freeze artifact를 독립 story로 관리 |
| tournament adapter/execution story 부재 | 후보가 문서에만 존재 | candidate integration과 staged tournament 실행 story 추가 |
| generic adapter가 model-specific template를 훼손 | 이미지/답안 성능 왜곡 | official processor/chat serialization golden + real-image smoke |
| AWQ dependency가 baseline을 오염 | 재현 실패 | 별도 environment/lock, engine-specific candidate id |
| sealed holdout 반복 확인 | local overfit | aggregate-only 공개와 version 폐기 규칙 |
| 65분대 기준선의 운영 여유 부족 | 70분 초과 위험 | 내부 63분 target, full-path projection과 early abort |
| GPU 준비 완료를 너무 일찍 선언 | 잘못된 full run | 10개 readiness check 모두 통과한 경우에만 사용자 알림 |

## Technical Research Recommendations

### Implementation Roadmap

1. 현재 기술 조사를 종합·확정한다.
2. Correct Course로 Reasoner v3 corrective story, Shadow Private corpus story, candidate adapter/tournament story와 GPU notification acceptance criterion을 Epic 3·4·5 통합 backlog에 반영한다.
3. 변경 후 implementation readiness를 다시 검사하고 sprint status를 생성한다.
4. Reasoner v3 schema/prompt/parser/Verifier/arbitration과 fail-closed submission을 구현한다.
5. diagnostic-48과 Shadow Private 300~600건을 구축·검수·동결한다.
6. Qwen7 → LLaVA7/MiniCPM → InternVL14 → 조건부 Qwen32-AWQ 순으로 staged tournament를 실행한다.
7. Reasoner-only shortlist 후 Verifier 조합을 비교한다.
8. runtime/compliance와 GPU readiness를 통과한 후보만 production submission으로 만든다.

### Technology Stack Recommendations

- Core: Python 3.10, PyTorch 2.6.0+cu124, modular CLI/package, YAML/JSONL/CSV artifacts.
- Baseline inference: in-process Transformers + official processor/chat template.
- Optimization: vLLM offline/local engine, engine-equivalence 통과 후 채택.
- Candidate isolation: model-specific adapter/config와 dependency lock/requirements.
- Evaluation: frozen Shadow Private manifest, deterministic metrics, immutable run comparison.
- Operations: persistent local storage, network-disabled production, atomic artifacts.

### Skill Development Requirements

- multimodal processor/chat template와 generated-token trimming 이해
- custom Hugging Face remote code와 snapshot/license audit
- CUDA memory/runtime measurement 및 batching trade-off
- validation split 봉인, subset metric과 overfitting 통제
- LLM-generated final answer 규칙과 fail-closed artifact lineage

### Success Metrics and KPIs

- compliance blocker: 0
- Reasoner/Verifier semantic invariant success: 100%
- uncertainty position 0/1/2 contract test: 모두 통과
- final candidate parse/image-load/unresolved failure: 0
- Shadow Private worst-subset 중대한 회귀: 0
- Verifier harmful flip이 beneficial flip 개선을 상쇄하지 않음
- exact model/prompt/data/environment hash coverage: 100%
- A6000 full-path peak VRAM: 48GB 물리 한도 내 안전 여유 확보
- internal projected total runtime: 63분 이하, official reference: 70분 이내
- GPU readiness 10개 gate: 10/10 후에만 `GPU_SUBMISSION_READY` 사용자 알림

## Research Synthesis

### Executive Summary

Public 0.91은 현재 Qwen2.5-VL-7B의 성능 상한을 입증하지 않는다. 실행 이력에는 label 의미 계약 오류와 runtime 경로 설명 불일치가 있었고, 독립 validation과 raw-output evidence가 충분하지 않았다. 따라서 모델을 즉시 교체하면 prompt contract, image preprocessing, model capacity와 engine 효과가 다시 섞인다.

가장 방어 가능한 전략은 `Reasoner v3 → Shadow Private → corrected Qwen control → model tournament → Verifier A/B → runtime/compliance → submission`이다. Public leaderboard는 local gate를 통과한 소수 후보의 sanity signal로만 사용한다. 이 방식은 확인할 수 없는 Private 점수를 독립 holdout으로 근사하고, 공개 점수에 대한 반복 적합을 줄인다.

**Key Technical Findings:**

- Multimodal label은 선택지 배열의 0-based 위치이며 숫자 자체에 uncertainty 의미가 없다.
- Reasoner v3와 Verifier는 `uncertainty_option_index`를 각각 생성하고 semantic invariant를 통과해야 한다.
- 300~600건 Shadow Private가 없으면 모델·Verifier·prompt 승격에 독립적인 근거가 없다.
- official processor/chat template와 image pipeline은 모델별로 보존해야 한다.
- 최신 vLLM 지원은 target A6000/PyTorch 2.6 환경의 품질·재현성·시간 합격을 대신하지 않는다.
- Qwen 7B는 폐기 대상이 아니라 corrected control이다.
- MiniCPM-V 4.5와 LLaVA-OneVision 7B가 1차 challenger, InternVL3-14B가 성능 중심 2차 후보, Qwen32-AWQ가 조건부 후보다.

### Technical Significance and Methodology

평가 규칙은 2026-05-31까지 공개된 가중치, 직접 관리 환경의 local inference, LLM 생성 텍스트 기반 최종 답변, offline 재현과 A6000 48GB 약 70분 경로를 요구한다. 따라서 leaderboard accuracy만 높은 실험보다 모델 revision, prompt/image lineage, generated candidate, runtime과 compliance가 함께 재현되는 실험이 기술적으로 우선한다.

조사는 다음 evidence hierarchy를 사용했다.

1. Multimodal 공식 규칙과 운영진 답변
2. 공식 model card/release 및 framework 문서
3. 현재 project source/config/tests와 기존 run 조사 artifact
4. 미검증 benchmark claim은 후보 우선순위 신호로만 사용

_Source:_ [Multimodal 평가 규칙 안내](공식 원문 링크 제외), [Transformers multimodal chat templates](https://huggingface.co/docs/transformers/chat_templating_multimodal), [vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models.html)

### Final Candidate Decision Framework

| 순서 | candidate | 역할 | 유지 조건 |
|---|---|---|---|
| Control | Qwen2.5-VL-7B BF16 Transformers | v2/v3와 기존 0.91 원인 분리 | exact revision, corrected contract, real-image audit |
| Challenger A | MiniCPM-V 4.5 BF16 Transformers | 8B 효율·OCR/vision 후보 | cutoff evidence, custom code audit, A6000 smoke |
| Challenger B | LLaVA-OneVision 7B Transformers | 낮은 integration-risk comparator | official template와 diagnostic 통과 |
| Performance | InternVL3-14B BF16 Transformers | 중형 성능 후보 | dynamic tiling, VRAM과 runtime 통과 |
| Conditional | Qwen2.5-VL-32B AWQ | 대형 양자화 후보 | isolated dependency, Shadow 품질, 70분 경로 통과 |

이 순서는 예상 순위가 아니라 평가 비용과 integration risk를 고려한 실행 순서다. winner는 frozen Shadow Private와 runtime/compliance gate로만 결정한다.

_Source:_ [Qwen2.5-VL-7B](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [MiniCPM-V 4.5](https://huggingface.co/openbmb/MiniCPM-V-4_5), [LLaVA-OneVision 7B](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-chat-hf), [InternVL3-14B](https://huggingface.co/OpenGVLab/InternVL3-14B), [Qwen2.5-VL-32B-AWQ](https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct-AWQ)

### Strategic Technical Recommendations

1. model change 전에 Reasoner v3를 구현해 label/uncertainty 의미를 닫는다.
2. diagnostic-48과 별개로 300~600건 Shadow Private를 구축·검수·동결한다.
3. 동일 Qwen snapshot/image/engine에서 v2와 v3를 먼저 비교한다.
4. model tournament는 Reasoner-only로 shortlist를 만든 후 Verifier를 별도 후보로 비교한다.
5. Public submission은 local gate를 통과한 상위 2~3개만 사용한다.
6. 전체 GPU production 전 readiness 10/10을 확인하고 사용자에게 `GPU_SUBMISSION_READY`를 알린다.

### Implementation Roadmap and BMad Handoff

**Phase 1 — Planning correction**

- Correct Course에 Reasoner v3 corrective story를 명시한다.
- Shadow Private corpus 구축·review·freeze story를 추가한다.
- model adapter/tournament execution story를 추가한다.
- GPU readiness 사용자 알림을 acceptance criterion으로 추가한다.

**Phase 2 — Readiness and sprint**

- 변경된 architecture/epics/stories의 implementation readiness를 재검사한다.
- Epic 3·4·5 통합 sprint-status를 생성한다.

**Phase 3 — Contract and validation foundation**

- Reasoner v3 schema/prompt/parser/Verifier/arbitration/submission guard를 구현한다.
- diagnostic-48과 Shadow Private 300~600건을 구축하고 hash로 동결한다.

**Phase 4 — Tournament and verification**

- Qwen control과 challengers를 staged gate로 실행한다.
- selection과 sealed holdout으로 shortlist를 확정한다.
- reasoner-only, same-model verifier, stronger-verifier를 별도 candidate로 평가한다.

**Phase 5 — Production and handoff**

- target A6000 full-path runtime/compliance를 검증한다.
- readiness 통과를 사용자에게 알린 뒤 8,500건 production을 실행한다.
- submission과 second-round artifacts를 감사한다.

### Risk Assessment

가장 큰 위험은 성능이 아니라 잘못된 실험 결론이다. contract와 validation이 없는 모델 비교, generic template 사용, holdout 반복 열람, AWQ dependency 혼합, Verifier의 규칙 기반 fallback은 모두 Public 개선처럼 보이면서 Private와 코드 검증을 악화시킬 수 있다. 각 위험은 immutable manifest, one-variable A/B, official serialization, sealed holdout, environment isolation과 fail-closed publication으로 통제한다.

### Future Technical Outlook

평가 기간의 near-term focus는 더 최신 모델을 계속 추가하는 것이 아니라 현재 eligible shortlist를 신뢰성 있게 비교하는 것이다. 이후 시간이 남으면 engine equivalence를 통과한 vLLM continuous batching, quantized larger model과 stronger triggered-only Verifier를 검토할 수 있다. fine-tuning이나 synthetic augmentation은 Shadow Private가 모델/contract 한계를 충분히 드러내고 외부 데이터 provenance와 leakage 검토가 완료된 뒤의 별도 단계다.

### Source Verification and Limitations

공식 규칙과 framework/model card는 2026-06-20 기준으로 확인했다. 다만 다음 값은 GPU evidence 전까지 미확정이다.

- 각 local snapshot의 exact immutable commit과 최초 공개 evidence
- 후보별 target environment dependency compatibility
- A6000 peak process VRAM과 전체 runtime
- Shadow Private 실제 성능과 최종 순위
- Verifier의 beneficial/harmful flip 효과

따라서 이 문서는 winner를 사전 선언하지 않고 tournament 진입·탈락 기준과 실행 순서를 확정한다.

### Technical Research Conclusion

현재 방향은 맞지만 implementation backlog가 완성되기 전 Epic 3·4·5를 바로 구현해서는 안 된다. 기술 조사 다음의 단일 올바른 작업은 Correct Course로 네 가지 누락—Reasoner v3 구현, Shadow Private corpus, model tournament, GPU notification gate—을 story와 acceptance criteria에 반영하는 것이다. 그 후 readiness 재검사와 sprint planning을 거쳐야 한다.

**Completion Date:** 2026-06-20  
**Source Verification:** 공식 규칙, 공식 framework 문서, 공식 model cards 및 local project artifacts  
**Confidence:** 전략·architecture는 높음; 최종 모델 순위와 GPU feasibility는 tournament 전까지 미확정
