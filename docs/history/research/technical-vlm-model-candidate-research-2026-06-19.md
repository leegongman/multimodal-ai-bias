---
stepsCompleted: [1, 2]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Multimodal 236722 1차 제출용 VLM 모델 후보 선정'
research_goals: '평가 규칙, 공개 코드공유, A6000 48GB 실행 가능성, Python 3.10/CUDA 12.4/PyTorch 2.6, 오프라인 실행, 라이선스, 2026-05-31 공개 가중치 조건을 확인해 1차 제출용 top 3, 성능 실험용 top 3, 제외 목록을 선정한다.'
user_name: 'gongman'
date: '2026-06-19'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-06-19
**Author:** gongman
**Research Type:** technical

---

## Research Overview

[Research overview and methodology will be appended here]

---

## Technical Research Scope Confirmation

**Research Topic:** Multimodal 236722 1차 제출용 VLM 모델 후보 선정
**Research Goals:** 평가 규칙, 공개 코드공유, A6000 48GB 실행 가능성, Python 3.10/CUDA 12.4/PyTorch 2.6, 오프라인 실행, 라이선스, 2026-05-31 공개 가중치 조건을 확인해 1차 제출용 top 3, 성능 실험용 top 3, 제외 목록을 선정한다.

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-06-19

## Technology Stack Analysis

### Programming Languages

Multimodal 236722 규칙상 최종 제출 및 검증 코드는 Python이어야 한다. 공식 규칙은 사용 가능 언어를 Python으로 제한하고, 최종 추론 코드는 운영진 기준 환경에서 실행 가능해야 한다고 명시한다. 기준 환경은 RTX A6000 48GB, Python 3.10, CUDA 12.4, PyTorch 2.6.0, Ubuntu 20.04다. 따라서 후보 모델은 Python 3.10과 PyTorch 2.6 계열에서 로컬 가중치 로드가 가능한 VLM이어야 하며, 원격 API 의존 후보는 제외해야 한다.

_Popular Languages:_ Python 3.10.
_Emerging Languages:_ 해당 없음. 평가 검증 언어 제약 때문에 Python 외 구현은 보조 스크립트 수준으로만 의미가 있다.
_Language Evolution:_ 모델 후보가 최신이어도 실행 코드는 Python 3.10 호환 문법과 라이브러리 버전을 유지해야 한다.
_Performance Characteristics:_ 병목은 언어 런타임보다 GPU 추론, 이미지 전처리, KV cache, batching, structured-output parsing이다.
_Source:_ [Multimodal 규칙](공식 원문 링크 제외)

### Development Frameworks and Libraries

핵심 프레임워크는 PyTorch, Hugging Face Transformers, vLLM/SGLang 계열이다. 현재 프로젝트는 `hf_local` adapter를 통해 `AutoProcessor`와 `AutoModelForImageTextToText`/모델 클래스 기반 로컬 로드를 지원하고 있으므로, 1차 제출은 Transformers로 닫을 수 있는 후보가 가장 구현 리스크가 낮다. Qwen2.5-VL 7B/32B, LLaVA-OneVision 7B, InternVL3-14B, MiniCPM-V 4.5, Molmo, GLM-4.1V 모두 Hugging Face 카드에서 `Image-Text-to-Text` 또는 Transformers 사용 경로를 제공한다. 다만 InternVL/MiniCPM/Molmo 계열은 `trust_remote_code=True` 또는 전용 chat API를 요구하는 경우가 있어 현재 adapter 수정 가능성을 별도로 봐야 한다.

_Major Frameworks:_ PyTorch, Transformers, vLLM, SGLang.
_Micro-frameworks:_ 모델별 유틸리티(`qwen-vl-utils`), PIL/Pillow 이미지 로딩, CSV/JSONL parser.
_Evolution Trends:_ Qwen2.5-VL과 Gemma 4 계열은 structured output, dynamic resolution, efficient vision encoder를 강조한다. MiniCPM-V 4.5는 소형 고성능과 압축된 visual token 처리를 강조한다.
_Ecosystem Maturity:_ Qwen2.5-VL과 LLaVA-OneVision은 baseline 및 HF/vLLM 경로가 가장 명확하다. InternVL/MiniCPM/Molmo/GLM은 성능 매력은 있으나 remote code, custom API, thinking-mode parsing 리스크가 더 크다.
_Source:_ [Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [Qwen2.5-VL-32B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct), [LLaVA-OneVision 7B](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-hf), [InternVL3-14B](https://huggingface.co/OpenGVLab/InternVL3-14B), [MiniCPM-V-4_5](https://huggingface.co/openbmb/MiniCPM-V-4_5), [Molmo-7B-D-0924](https://huggingface.co/allenai/Molmo-7B-D-0924), [GLM-4.1V-9B-Thinking](https://huggingface.co/zai-org/GLM-4.1V-9B-Thinking)

### Database and Storage Technologies

이 프로젝트는 데이터베이스가 필요하지 않다. 평가 제출 파이프라인의 저장 계층은 로컬 파일 시스템의 CSV/JSONL/YAML artifact다. 공식 test 8,500건 규모에서는 SQLite나 object store를 추가할 이유가 없고, BMad architecture의 감사 가능성 요구도 `runs/{run_id}` 로컬 artifact 구조로 충분하다. 중요한 것은 `raw_reasoner.jsonl`, `parsed_reasoner.csv`, `submission.csv`, `config.resolved.yaml`, 모델 config, prompt version을 불변 artifact로 남기는 것이다.

_Relational Databases:_ 불필요.
_NoSQL Databases:_ 불필요.
_In-Memory Databases:_ 불필요.
_Data Warehousing:_ 불필요.
_Source:_ [Multimodal 데이터/제출 형식 요구](공식 원문 링크 제외), 로컬 Story 2.6 제출 artifact contract.

### Development Tools and Platforms

개발 도구는 `uv`, `pytest`, `ruff`, Hugging Face local snapshot 관리, GPU 실행 로그가 중심이다. 현재 프로젝트는 Python 3.10 범위로 고정되어 있고, `uv run multimodal-bias` CLI가 `validate-data`, `smoke-model`, `infer`, `make-submission`, `verify-risky`를 제공한다. 모델 선정 단계에서는 후보마다 최소 `smoke-model`과 소규모 fixture inference를 먼저 통과시킨 뒤 full 8,500 추론으로 넘어가야 한다.

_IDE and Editors:_ 모델 선정에는 영향 없음.
_Version Control:_ 현재 workspace는 git repo가 아니므로 모델 config와 실험 로그를 파일 artifact로 더 엄격히 남겨야 한다.
_Build Systems:_ `uv` 기반 dependency/run 관리.
_Testing Frameworks:_ `pytest`, `ruff`; 모델 후보 검증은 별도 GPU smoke/inference benchmark가 필요하다.
_Source:_ 로컬 `pyproject.toml`, `src/multimodal_bias/cli.py`, [Multimodal 규칙](공식 원문 링크 제외)

### Cloud Infrastructure and Deployment

원격 API 추론은 금지된다. Multimodal 규칙은 OpenAI API, Gemini API, Hugging Face Inference API, Together AI, OpenRouter 등 원격 서버를 통한 모델 응답 사용을 금지하고, 참가자가 직접 관리하는 PC/클라우드/연구실 서버에서 모델 가중치를 직접 로드하는 방식만 허용한다. 따라서 클라우드는 가능하지만, managed inference API가 아니라 GPU VM에서 로컬 snapshot을 로드하는 구조여야 한다. 운영진 검증 환경은 A6000 48GB 기준이므로 H100/A100에서만 돌아가는 후보는 1차 제출 주력 후보에서 낮춰야 한다.

_Major Cloud Providers:_ 사용 가능하나 self-managed GPU VM 형태여야 한다.
_Container Technologies:_ Docker/vLLM/SGLang 사용 가능성은 있지만 최종 재현성 문서화가 필요하다.
_Serverless Platforms:_ 부적합. 모델 가중치 직접 로드와 GPU 장시간 추론에 맞지 않다.
_CDN and Edge Computing:_ 부적합.
_Source:_ [Multimodal 규칙](공식 원문 링크 제외)

### Technology Adoption Trends

공식 baseline은 `llava-hf/llava-onevision-qwen2-0.5b-si-hf`와 vLLM guided 추론을 사용한다. 공개 고득점 신호는 Qwen 계열 9B/27B급 모델, evidence-only prompt, uncertainty option 처리, Reasoner/Verifier 2-pass 구조다. 다만 Public 0.99633 코드 공유 작성자는 큰 모델이 Public에 유리한 경향을 보이지만 GPU 비용, 추론 시간, Private 일반화를 함께 봐야 한다고 언급했고, 해당 글의 댓글 맥락에서는 Public 기준으로 verifier 제거가 더 좋았다는 신호도 있다. 따라서 1차 제출은 무조건 2-pass가 아니라 Reasoner-only 강한 후보를 먼저 돌리고, Verifier는 local validation 이후 조건부로 붙이는 흐름이 합리적이다.

_Migration Patterns:_ baseline 0.5B에서 7B/9B/14B/27B급 Reasoner로 이동.
_Emerging Technologies:_ structured-output capable VLM, vLLM/SGLang serving, dynamic visual token budgeting, thinking-mode VLM.
_Legacy Technology:_ 0.5B baseline은 smoke용으로 남기되 성능 후보로는 낮다.
_Community Trends:_ Multimodal 코드공유에서는 Qwen 계열 큰 모델과 evidence-grounded prompt가 강한 신호다.
_Source:_ [Multimodal baseline 코드공유](공식 원문 링크 제외), [Public 0.99633 코드공유](공식 원문 링크 제외), [Multimodal 규칙](공식 원문 링크 제외)

## Integration Patterns Analysis

### API Design Patterns

이 프로젝트의 1차 제출 경로는 in-process Python API가 가장 안전하다. Multimodal은 원격 API 기반 모델 응답 사용을 금지하지만, 참가자가 관리하는 서버에서 직접 가중치를 로드하는 것은 허용한다. 따라서 `Transformers`를 같은 Python 프로세스에서 직접 호출하는 방식이 규칙/감사/재현성 측면에서 가장 단순하다. vLLM/SGLang은 로컬 self-managed serving으로 쓸 수 있지만, OpenAI-compatible HTTP API 형태를 쓰면 “원격 API 금지”와 혼동될 수 있으므로 1차 제출에서는 직접 로드가 우선이다. vLLM은 Qwen2.5-VL, LLaVA-OneVision, InternVL, MiniCPM 계열 모델 카드에서 지원 경로로 제시되지만, 운영진 검증 시 추가 서버 프로세스와 포트/IPC/컨테이너 재현성을 설명해야 한다.

_RESTful APIs:_ 1차 제출 주력 방식으로 부적합. 로컬 vLLM/SGLang 서버는 가능하더라도 검증 복잡도가 오른다.
_GraphQL APIs:_ 부적합.
_RPC and gRPC:_ 부적합.
_Webhook Patterns:_ 부적합.
_Source:_ [Multimodal 규칙](공식 원문 링크 제외), [Qwen2.5-VL-7B model card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [LLaVA-OneVision 7B model card](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-hf), [MiniCPM-V-4_5 model card](https://huggingface.co/openbmb/MiniCPM-V-4_5)

### Communication Protocols

제출 파이프라인 내부 통신은 프로세스 내부 함수 호출과 로컬 파일 artifact가 중심이어야 한다. 공식 규칙은 오프라인 환경에서 외부 API 호출 또는 인터넷 통신을 허용하지 않는다. 따라서 모델 snapshot은 사전에 내려받아 두고, 모델 config는 `local_files_only: true`를 강제해야 한다. 현재 repo의 `hf_local` adapter는 Hugging Face `from_pretrained(..., local_files_only=True)` 경로에 맞춰져 있어 규칙상 적합하다.

_HTTP/HTTPS Protocols:_ 모델 다운로드/원격 추론에는 최종 실행 중 사용 금지. 로컬 vLLM HTTP도 1차 제출에서는 후순위.
_WebSocket Protocols:_ 부적합.
_Message Queue Protocols:_ 불필요.
_grpc and Protocol Buffers:_ 불필요.
_Source:_ [Multimodal 규칙](공식 원문 링크 제외), [Qwen2.5-VL-7B Transformers/vLLM usage](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)

### Data Formats and Standards

평가와 현재 repo 모두 CSV/JSONL/YAML 중심이다. 입력은 official `test.csv`와 이미지 파일, prompt/model 설정은 YAML, raw model output은 JSONL, parsed prediction과 submission은 CSV다. 모델 출력은 가능한 한 strict JSON marker를 포함한 텍스트로 생성시키고, 최종 label은 LLM 생성 텍스트에서 파싱해야 한다. Multimodal 규칙상 단순 룰 기반 label 결정은 허용되지 않으므로, unknown option regex나 fallback은 제출 안정화 보조 장치로만 제한해야 한다.

_JSON and XML:_ JSON은 모델 출력 계약에 적합하다. XML은 불필요.
_Protobuf and MessagePack:_ 불필요.
_CSV and Flat Files:_ 공식 제출 형식과 run artifact에 필수.
_Custom Data Formats:_ `raw_reasoner.jsonl`, `parsed_reasoner.csv`, `final_predictions.csv`, `submission.csv`, prompt YAML.
_Source:_ [Multimodal 규칙](공식 원문 링크 제외), [Qwen2.5-VL structured output 언급](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)

### System Interoperability Approaches

모델별 current-repo 호환성은 다음과 같이 갈린다.

| 모델 계열 | 현재 repo 연결 방식 | 추가 작업 | 1차 제출 적합성 |
|---|---|---:|---|
| Qwen2.5-VL 7B/32B | `AutoProcessor` + HF model class 또는 Qwen 전용 class | `qwen-vl-utils`, 최신 Transformers, 이미지 처리 smoke 필요 | 높음 |
| LLaVA-OneVision 7B/0.5B | `AutoProcessor` + `AutoModelForMultimodalLM`/ImageTextToText 경로 | 낮음. baseline 계열이라 검증 쉬움 | 중간-높음 |
| Gemma 4 | `AutoProcessor` + Gemma 전용 conditional generation class 가능성 | Gemma 4 HF repo/라이선스/로컬 snapshot 확인, adapter class 확인 | 보류 |
| InternVL3 | `AutoModel` + `AutoTokenizer` + `model.chat`, `trust_remote_code=True` | 별도 adapter 필요 | 성능 후보, 1차 바로 실행은 낮음 |
| MiniCPM-V | `AutoModel` + `AutoTokenizer` + `model.chat`, `trust_remote_code=True` | 별도 adapter 필요. cutoff 확인 필요 | 성능 후보, 1차 바로 실행은 낮음 |
| Phi-4 multimodal | `AutoModelForCausalLM`, `trust_remote_code=True`, multimodal LoRA/format | 별도 adapter 및 image prompt 형식 확인 | 보류 |
| Molmo | `AutoProcessor`, `trust_remote_code=True`, custom generation pattern | 별도 adapter/출력 파싱 필요 | 보류 |
| GLM-4.1V | `Glm4vForConditionalGeneration`, thinking output | thinking tag 제거/JSON parsing 보정 필요. 공개일이 2025-07이라 cutoff 이전이지만 Multimodal 2026-05-31 기준은 통과 | 성능 실험 후보 |

_Point-to-Point Integration:_ 현재는 CLI -> local adapter -> run artifact로 충분하다.
_API Gateway Patterns:_ 부적합.
_Service Mesh:_ 부적합.
_Enterprise Service Bus:_ 부적합.
_Source:_ [Qwen2.5-VL-7B](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [LLaVA-OneVision 7B](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-hf), [InternVL3-14B](https://huggingface.co/OpenGVLab/InternVL3-14B), [MiniCPM-V-4_5](https://huggingface.co/openbmb/MiniCPM-V-4_5), [Phi-4 multimodal](https://huggingface.co/microsoft/Phi-4-multimodal-instruct), [Molmo-7B-D-0924](https://huggingface.co/allenai/Molmo-7B-D-0924), [GLM-4.1V-9B-Thinking](https://huggingface.co/zai-org/GLM-4.1V-9B-Thinking), [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)

### Microservices Integration Patterns

이 프로젝트는 microservices로 나눌 필요가 없다. 모델 추론 서버를 별도 프로세스로 띄우면 throughput은 좋아질 수 있지만, 1차 제출의 주요 리스크인 규칙 준수, reproducibility, artifact audit가 복잡해진다. vLLM/SGLang은 32B급 이상을 성능 실험할 때 검토하고, 1차 제출은 in-process Transformers로 먼저 닫는 것이 좋다.

_API Gateway Pattern:_ 부적합.
_Service Discovery:_ 부적합.
_Circuit Breaker Pattern:_ model inference failure를 per-sample artifact로 기록하는 정도면 충분하다.
_Saga Pattern:_ 부적합.
_Source:_ [Multimodal 규칙](공식 원문 링크 제외), [Qwen2.5-VL vLLM usage](https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct)

### Event-Driven Integration

Event-driven architecture는 이 평가 제출 경로에 필요하지 않다. 배치 inference 작업이므로 queue/event broker보다 deterministic ordered iteration과 per-sample failure logging이 더 중요하다. 재시도도 queue retry가 아니라 run artifact 기반으로 명시적으로 관리해야 한다.

_Publish-Subscribe Patterns:_ 부적합.
_Event Sourcing:_ 모델 output artifact가 감사 로그 역할을 일부 수행한다.
_Message Broker Patterns:_ 불필요.
_CQRS Patterns:_ 불필요.
_Source:_ [Multimodal 규칙](공식 원문 링크 제외)

### Integration Security Patterns

보안/검증 관점의 핵심은 네트워크를 끄고도 동일하게 실행되는가다. 모델 가중치, processor/tokenizer, custom code, prompt template, config, dependency version을 모두 로컬에 고정해야 한다. `trust_remote_code=True` 후보는 실행 전 해당 snapshot의 코드와 라이선스를 산출물에 기록해야 하며, 검증 단계에서 임의 원격 code fetch가 발생하지 않도록 `local_files_only=True`와 snapshot hash를 강제해야 한다.

_OAuth 2.0 and JWT:_ 부적합.
_API Key Management:_ 최종 실행에는 HF token/API key가 필요하지 않아야 한다.
_Mutual TLS:_ 부적합.
_Data Encryption:_ 평가 제출 자체에는 필수 아님. 로컬 artifact 무결성/경로 안전성이 더 중요하다.
_Source:_ [Multimodal 규칙](공식 원문 링크 제외), [Gemma Terms/Gemma 4 license context](https://ai.google.dev/gemma/docs/core/model_card_4), [Phi-4 multimodal model card](https://huggingface.co/microsoft/Phi-4-multimodal-instruct)

<!-- Content will be appended sequentially through research workflow steps -->
