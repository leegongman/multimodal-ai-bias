# 대화 001 - RunPod GPU 제출 파이프라인 및 Qwen vLLM 문제 정리

## 목적

Multimodal 236722 멀티모달 AI Bias 프로젝트용 1차 제출물을 만들기 위해, 기존 BMad 기반 프로젝트 진행 상태를 확인하고 RunPod A6000 GPU 환경에서 공식 데이터, 모델 가중치, 추론 파이프라인, vLLM 실행 경로를 준비·검증하려 했다.

## 핵심 요약

이 대화에서는 먼저 BMad 흐름으로 Story 1.1 이후 여러 story review와 patch 적용을 진행했고, 이후 Epic 3 진행을 멈추고 1차 제출물 생성에 집중하기로 했다. 1차 제출 모델 후보를 검토한 뒤 MiniCPM-V-4_5를 먼저 시도했으나, transformers 기반 순차 추론 속도가 8500개 기준 70분 안에 들어오기 어렵다는 문제가 확인됐다. 이후 Qwen/Qwen2.5-VL-7B-Instruct로 모델을 바꾸고 RunPod A6000 48GB 환경에서 실행을 시도했다. Qwen HF local 경로도 성공 추론 기준으로는 약 3초 이상/sample 수준이라 70분 조건에 부적합했다. 속도 개선을 위해 vLLM 서버 및 vLLM offline batch 경로를 검토했지만, vLLM 0.10.2와 Qwen2.5-VL snapshot/config 호환 문제로 서버 기동이 아직 완료되지 않았다. RunPod 파일 전송, 공식 데이터 압축 해제, 데이터 경로 보정, 모델 다운로드, GPU dependency 설치 일부는 성공했다. 최종 제출 가능한 `submission.csv` 생성은 아직 완료되지 않았다. 현재 핵심 미해결 문제는 Qwen2.5-VL-7B를 vLLM에서 정상 로드하고, 70분 내 전체 test 추론이 가능한 batch 제출 경로를 확보하는 것이다.

## 시도한 작업

| 순서 | 시도한 내용 | 사용한 방법·명령어 | 결과 |
| -- | ------ | ---------- | --------------- |
| 1 | BMad 초기 계획 산출물 확인 | `docs/history/architecture.md`, `epics.md`, `implementation-readiness-report-2026-06-18.md` 확인 | 성공 |
| 2 | Story 1.1 code review patch 처리 | Python runtime range 고정, CLI help/version 테스트, cache ignore/test, scaffold artifact guard 추가 지시 | 성공 여부는 대화 요약상 완료로 언급됨 |
| 3 | Story 1.2~3.2 review/개발 흐름 진행 | `bmad-code-review`, `bmad-create-story`, `bmad-dev-story` 등 반복 | 세부 결과 확인되지 않음 |
| 4 | Epic 3 진행 중단 및 1차 제출 우선순위 전환 | 사용자 지시: “3는 멈추고 1차 제출용” | 성공 |
| 5 | 모델 후보 검토 요청 | `bmad-technical-research`로 Qwen, InternVL, LLaVA-OneVision, Gemma, MiniCPM, Phi, Molmo, GLM 계열 검토 요청 | 연구 산출물 존재 확인, 세부 후보 검증은 이 문서 범위에서 확인되지 않음 |
| 6 | 1차 시도 모델을 MiniCPM-V-4_5로 선택 | 사용자 결정: “MiniCPM-V-4_5 먼저 해보자” | 성공 |
| 7 | RunPod SSH 접속 시도 | 호스트·포트·사용자명·키 경로를 비식별화한 SSH 절차 | 실패 |
| 8 | SSH public key 확인 | `cat ~/.ssh/id_ed25519.pub` | 성공 |
| 9 | 잘못된 터미널에서 `/root/.ssh` 생성 시도 | `mkdir -p /root/.ssh`, `authorized_keys` 수정 명령 | 실패, Mac 로컬에서 실행되어 `/root: Read-only file system` |
| 10 | VS Code Remote로 RunPod 연결 | 사용자가 “좋아 vs에도 연결했어”라고 확인 | 성공 |
| 11 | RunPod GPU/기본 환경 확인 | `nvidia-smi`, `python --version`, `uv --version` | 성공, A6000 48GB/CUDA 12.4/uv 0.9.0 확인 |
| 12 | RunPod root에서 프로젝트 명령 실행 | `uv sync`, `uv run pytest` | 실패, `/`에 `pyproject.toml` 없음 |
| 13 | Runtime zip 생성/전송 준비 | `pyproject.toml`, `uv.lock`, `.python-version`, `configs/`, `src/`, `tests/`, `conftest.py` zip 요청 | 부분 성공, 경로 혼선 발생 |
| 14 | RunPod에서 runtime zip 압축 해제 | `/workspace/multimodal-bias/multimodal-bias-runtime.zip` 사용 | 성공 여부 일부 확인, 이후 프로젝트 명령 실행 가능해짐 |
| 15 | MiniCPM-V-4_5 가중치 다운로드 | `uv run --with huggingface_hub hf download openbmb/MiniCPM-V-4_5 --local-dir models/snapshots/MiniCPM-V-4_5 --max-workers 1` | 성공, 17.4GB/23 files |
| 16 | 공식 데이터 `open.zip` 확인 | `find /workspace -iname 'open.zip' ...` | 최초 실패, RunPod에 없음 |
| 17 | `open.zip` 업로드 시도 | `scp -C ... ~/Downloads/open.zip ...` | 실패, macOS `Operation not permitted` |
| 18 | `open.zip` 업로드 재시도 | 비식별화한 원격 전송 절차로 `open.zip`을 RunPod 프로젝트에 전송 | 성공, 2.898GB 전송 완료 |
| 19 | 공식 데이터 압축 해제 및 validate | `unzip open.zip -d data/raw/open`, `uv run multimodal-bias validate-data --data-root data/raw/open` | 최초 실패 후 CSV image_path 보정으로 해결된 것으로 대화 요약에 기록 |
| 20 | MiniCPM smoke test | `uv run multimodal-bias smoke-model --model-config configs/models/minicpm_v_4_5.yaml --image-path data/raw/open/test/images/test_img_0000.jpg` | 최초 dependency 오류 후 성공 |
| 21 | MiniCPM full inference | `uv run --no-sync multimodal-bias infer --config configs/base.yaml --model-config configs/models/minicpm_v_4_5.yaml` | 중단/부적합, 약 252개 진행 기준 8시간대 추정 |
| 22 | MiniCPM vLLM 시도 | `vllm serve ... MiniCPM-V-4_5 ...` | 실패, tokenizer 호환 오류 |
| 23 | Qwen2.5-VL-7B 다운로드 | `uv run --with huggingface_hub hf download Qwen/Qwen2.5-VL-7B-Instruct --local-dir models/snapshots/Qwen2.5-VL-7B-Instruct --max-workers 4` | 최초 `click` 누락 오류 후 사용자가 완료했다고 확인 |
| 24 | Qwen HF local full inference | `uv run --no-sync multimodal-bias infer --config configs/base.yaml --model-config configs/models/qwen2_5_vl_7b.yaml` | 실패 또는 부적합, `Invalid device string: '0'` 및 느린 성공 추론 확인 |
| 25 | Qwen device string 문제 수정 | `hf_vlm.py`에서 device `"0"`을 `"cuda:0"`로 매핑하는 방향 | 부분 성공, generated row가 나오기 시작 |
| 26 | Qwen HF local 속도 확인 | `.raw_reasoner.jsonl.tmp` line count 및 elapsed 계산 | 실패/부적합, 성공 추론 기준 약 495~536분 추정 |
| 27 | Qwen vLLM server 시도 | `vllm serve ... Qwen2.5-VL-7B-Instruct ... --max-model-len 4096` | 실패, rope config 충돌 |
| 28 | Qwen snapshot rope config 패치 | `config.json`의 `rope_scaling` legacy `type`을 `rope_type`으로 조정 | 부분 성공, 다음 오류로 진행 |
| 29 | vLLM tokenizer fallback 패치 | `/workspace/vllm-minicpm/.../vllm/transformers_utils/tokenizer.py`에서 `all_special_tokens_extended` fallback 적용 | 부분 성공, 다음 오류로 진행 |
| 30 | Qwen preprocessor min/max pixels 패치 | `preprocessor_config.json`에 `min_pixels=200704`, `max_pixels=602112` 추가 | 부분 성공, 직접 속성 접근 오류는 추가 패치 필요 |
| 31 | vLLM qwen2_vl.py min/max pixels fallback 패치 | `/workspace/vllm-minicpm/.../vllm/model_executor/models/qwen2_vl.py`의 `image_processor.min_pixels/max_pixels`를 `getattr(..., fallback)`으로 변경 | 부분 성공, 다음 오류로 진행 |
| 32 | vLLM V1 engine 기동 확인 | `tail -f /workspace/qwen_vllm.log` | 실패, `Qwen2_5_VLConfig`에 `vocab_size` 없음 오류 |
| 33 | Qwen config top-level text_config 복사 패치 시도 | `config.json`에서 `text_config`를 읽어 top-level로 복사하려 함 | 실패, `text_config` object 없음 |
| 34 | vLLM V0 engine 전환 제안 | `nohup env VLLM_USE_V1=0 CUDA_VISIBLE_DEVICES=0 vllm serve ...` | 최종 성공 여부 확인되지 않음 |

## 성공한 내용

- RunPod GPU 환경 접속 및 VS Code Remote 연결이 완료됐다.
- RunPod에서 `nvidia-smi`로 NVIDIA RTX A6000 48GB, Driver `550.127.08`, CUDA `12.4`가 확인됐다.
- MiniCPM-V-4_5 Hugging Face snapshot 다운로드가 완료됐다.
- Qwen/Qwen2.5-VL-7B-Instruct snapshot 다운로드가 완료됐다고 사용자가 확인했다.
- `open.zip`은 `rsync`로 RunPod `/workspace/multimodal-bias/open.zip`에 전송 완료됐다.
- 공식 데이터의 `./images/...` 경로 문제는 `train/images/...`, `test/images/...` 형태로 보정하는 접근을 사용했다.
- MiniCPM smoke-model은 dependency 수정 후 실제 이미지에 대해 모델 로드 및 생성까지 성공했다.
- Qwen HF local 경로는 device string 보정 후 일부 generated row가 생성되는 상태까지 도달했다.
- vLLM Qwen 서버 기동 과정에서 rope config 오류, tokenizer 오류, min_pixels 오류를 순차적으로 지나가도록 패치가 적용됐다.

## 실패하거나 중단된 내용

- 초기 SSH 접속은 public key 인증 실패 또는 port refused로 실패했다.
- `/root/.ssh` 설정 명령을 Mac 로컬 터미널에서 실행해 실패했다.
- RunPod `/` 또는 Mac 로컬에서 `/workspace/multimodal-bias` 명령을 실행해 `pyproject.toml` 또는 파일 없음 오류가 발생했다.
- `scp`로 `~/Downloads/open.zip`을 전송하려던 시도는 macOS 권한 문제로 실패했다.
- MiniCPM transformers 기반 full inference는 너무 느려 70분 조건에 부적합했다.
- Qwen HF local full inference도 순차 추론 병목 때문에 70분 조건에 부적합했다.
- `20260619_041654_default` run은 `raw_reasoner.jsonl`, `parsed_reasoner.csv`가 생겼지만 모든 row가 `source_failed`였고 제출 생성에 실패했다.
- Qwen vLLM server는 아직 `Application startup complete`까지 확인되지 않았다.
- vLLM offline batch 스크립트는 대화 중 제안됐지만 실제 생성·실행 완료는 확인되지 않았다.

## 발생한 오류와 원인

| 오류 메시지 | 확인된 원인 | 추정 원인 |
| -- | -- | -- |
| `Permission denied (publickey)` | SSH public key 인증 실패 | RunPod UI 등록 key와 로컬 private key 쌍 불일치 가능성 |
| `ssh: connect to host ... port ...: Connection refused` | 해당 host/port로 SSH 접속 불가 | Pod 변경, 포트 변경, SSH 서비스 미기동 가능성 |
| `mkdir: /root: Read-only file system` | `/root/.ssh` 명령을 RunPod가 아니라 Mac 로컬에서 실행 | 해당 없음 |
| `No pyproject.toml found` | 프로젝트 루트가 아닌 디렉터리에서 `uv sync` 실행 | 해당 없음 |
| `No module named 'torchvision'` | MiniCPM smoke 시 `torchvision` 미설치 | GPU dependency 세트 미완성 |
| `undefined symbol: ncclCommResume` | PyTorch/CUDA/NCCL wheel 조합 불일치 | `uv run --with` 또는 dependency sync 과정에서 torch 계열 wheel이 교체됐을 가능성 |
| `No module named pip` | `.venv` Python에 pip가 없음 | `uv` venv 특성 또는 pip 미설치 |
| `Invalid Multimodal data layout ... image_path is not under test/images` | 공식 CSV의 image_path가 `./images/...` 형태였고 프로젝트 validator는 split-relative path를 요구 | 해당 없음 |
| `bash: syntax error near unexpected token newline` | `<생성된_run_id>` placeholder를 실제 값 대신 그대로 실행 | 해당 없음 |
| `Submission invalid: parsed Reasoner row 2 parsed_label must be exactly 0, 1, or 2` | parsed row가 valid label을 갖지 않음 | 원인은 Qwen HF local run이 모두 `source_failed`였기 때문 |
| `Invalid device string: '0'` | Qwen HF local adapter에 잘못된 device string 전달 | device 값 정규화 부족 |
| `ModuleNotFoundError: No module named 'click'` | `uv run --with huggingface_hub hf` 실행 시 CLI dependency 누락 | project `.venv`를 임시 download 명령으로 오염시킨 영향 가능성 |
| `Found conflicts between 'rope_type=default' and 'type=mrope'` | Qwen config의 rope scaling legacy/modern field 충돌 | vLLM 0.10.2와 snapshot config 호환성 문제 |
| `MiniCPMVTokenizerFast has no attribute all_special_tokens_extended` | tokenizer 객체가 vLLM이 기대하는 속성을 제공하지 않음 | vLLM/tokenizer 버전 호환 문제 |
| `Qwen2Tokenizer has no attribute all_special_tokens_extended` | 동일하게 vLLM tokenizer helper가 없는 속성에 직접 접근 | vLLM/tokenizer 버전 호환 문제 |
| `Qwen2VLImageProcessor object has no attribute min_pixels` | vLLM qwen2_vl 코드가 image processor의 `min_pixels` 속성에 직접 접근 | processor config/transformers/vLLM 조합 불일치 |
| `Qwen2_5_VLConfig object has no attribute vocab_size` | vLLM V1 engine이 Qwen2.5-VL config를 language model config처럼 처리 | vLLM 0.10.2 V1 engine의 Qwen2.5-VL 호환 문제 가능성 |

## 결정사항

- Epic 3/4/5의 verifier/selection 고도화보다, 먼저 Epic 1/2 기반 제출 파이프라인으로 1차 제출물을 만드는 것을 우선한다.
- 제출물 생성은 실제 최종 실행 환경과 같은 GPU 제약 안에서 돌아야 한다.
- A6000 48GB 환경에서 실행 가능한 모델을 사용해야 하며, 과도하게 큰 GPU로 만든 제출물은 최종본 기준에 맞지 않는다는 원칙을 확인했다.
- MiniCPM-V-4_5는 smoke는 가능했지만 full inference가 너무 느려 1차 제출 본선 경로에서 보류됐다.
- Qwen/Qwen2.5-VL-7B-Instruct를 다음 주요 시도 모델로 사용했다.
- HF transformers sequential `multimodal-bias infer` 경로는 70분 목표에 부적합하므로 vLLM batch/offline 또는 vLLM server 기반 접근이 필요하다고 판단했다.
- RunPod 원격에서 작업 중일 때 로컬 파일 수정만으로는 의미가 없으며, 실제 실행은 `/workspace/multimodal-bias`에서 진행해야 한다.
- `uv run --with huggingface_hub`를 프로젝트 `.venv`에서 반복 사용하면 dependency가 바뀔 수 있으므로 별도 Hugging Face download env를 쓰는 방향이 정리됐다.

## 변경된 파일

| 파일 경로 | 변경 유형 | 변경 내용 | 현재 상태 |
| ----- | ----------------- | ----- | ---------- |
| `/Applications/학교 외부/멀티모달 AI Bias/requirements-gpu-minicpm-cu124.txt` | 생성 | MiniCPM용 CUDA 12.4 GPU dependency pin 파일 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/configs/models/qwen2_5_vl_7b.yaml` | 생성 | Qwen2.5-VL-7B local HF model config | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/requirements-gpu-qwen2-5-vl-cu124.txt` | 생성 | Qwen2.5-VL용 CUDA 12.4 dependency pin 파일 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/docs/history/runpod-qwen2-5-vl-7b-reproduction-2026-06-19.md` | 생성 | RunPod Qwen2.5-VL-7B 재현 절차 문서 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/multimodal-bias-runtime.zip` | 생성 | RunPod 업로드용 runtime zip | 완료 여부 확인 필요 |
| `/workspace/multimodal-bias/open.zip` | 생성/이동 | 로컬 `open.zip`을 RunPod 프로젝트로 전송 | 완료 |
| `/workspace/multimodal-bias/data/raw/open` | 생성/수정 | 공식 데이터 압축 해제 및 CSV image_path 보정 | 완료로 대화상 추정, 현재 원격 상태는 확인 필요 |
| `/workspace/multimodal-bias/models/snapshots/MiniCPM-V-4_5` | 생성 | MiniCPM-V-4_5 snapshot 다운로드 | 완료 |
| `/workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct` | 생성 | Qwen2.5-VL-7B snapshot 다운로드 | 완료로 사용자 확인 |
| `/workspace/multimodal-bias/models/snapshots/MiniCPM-V-4_5/tokenization_minicpmv_fast.py` | 수정 | `all_special_tokens_extended` fallback 성격의 tokenizer 호환 패치 | 완료 여부 확인 필요 |
| `/workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct/config.json` | 수정 | `rope_scaling`의 legacy `type`/modern `rope_type` 충돌 대응 | 완료 |
| `/workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct/preprocessor_config.json` | 수정 | `min_pixels`, `max_pixels` 추가 | 완료 |
| `/workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/transformers_utils/tokenizer.py` | 수정 | `all_special_tokens_extended` 없을 때 `all_special_tokens` fallback | 완료 |
| `/workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/model_executor/models/qwen2_vl.py` | 수정 | `image_processor.min_pixels/max_pixels` 직접 접근을 `getattr(..., fallback)`으로 변경 | 완료 |
| `/workspace/qwen_vllm.log` | 생성/수정 | Qwen vLLM server 로그 파일 | 완료 |
| `/workspace/multimodal-bias/runs/20260619_041654_default/raw_reasoner.jsonl` | 생성 | Qwen HF local inference raw output | 생성됐으나 전 row 실패 |
| `/workspace/multimodal-bias/runs/20260619_041654_default/parsed_reasoner.csv` | 생성 | parsed Reasoner output | 생성됐으나 제출 불가 |
| `/workspace/multimodal-bias/scripts/run_qwen_vllm_offline.py` | 생성 제안 | vLLM offline batch 스크립트 | 생성되지 않음 |
| `/Applications/학교 외부/멀티모달 AI Bias/docs/history/conversation-001-runpod-vllm-qwen-submission-summary-2026-09-02.md` | 생성 | 이 대화 정리 문서 | 완료 |

## 현재 상태

진행 중.

프로젝트의 기본 제출 파이프라인과 RunPod GPU 실행 환경 준비는 상당 부분 진행됐다. 하지만 최종 목표인 Multimodal 제출용 `submission.csv` 생성은 아직 완료되지 않았다. 특히 Qwen2.5-VL-7B를 vLLM으로 정상 로드하고 8500개 test sample을 70분 이내에 처리하는 경로가 아직 검증되지 않았다.

## 미해결 사항

- `VLLM_USE_V1=0`으로 vLLM V0 engine을 강제했을 때 Qwen2.5-VL-7B server가 실제로 `Application startup complete`까지 도달하는지 확인되지 않았다.
- vLLM server 방식과 vLLM offline batch 방식 중 어떤 경로가 최종 제출 생성에 쓰일지 확정되지 않았다.
- Qwen2.5-VL-7B vLLM 추론 결과가 기존 `FINAL_ANSWER_JSON` 계약을 안정적으로 만족하는지 확인되지 않았다.
- 8500개 전체 추론의 실제 wall-clock 시간은 확인되지 않았다.
- `submission.csv` 최종 생성 및 Multimodal 제출 성공 여부는 확인되지 않았다.
- Public LB 점수, private/hidden 일반화 성능, 최종 후보 선정 기준은 이 대화에서 실행 검증되지 않았다.
- RunPod 원격에 적용된 site-packages 패치는 재생성 가능한 설치 절차로 아직 정리되지 않았다.

## 다음 작업

1. RunPod에서 `VLLM_USE_V1=0` 실행 결과를 확인한다.
2. vLLM server가 뜨면 `/v1/models`와 단일 이미지 요청으로 smoke test를 수행한다.
3. server가 계속 실패하면 server 방식을 접고 vLLM offline `LLM.generate()` batch 스크립트를 RunPod `/workspace/multimodal-bias/scripts/`에 생성한다.
4. 20~100개 샘플로 batch throughput과 `FINAL_ANSWER_JSON` parse 성공률을 측정한다.
5. 70분 이내가 가능한 설정으로 `max_tokens`, 이미지 pixel limit, batch size/concurrency를 고정한다.
6. 전체 8500개 추론을 실행하고 `raw_reasoner.jsonl`, `parsed_reasoner.csv`, `submission.csv`를 생성한다.
7. 제출 파일 row count, sample_id 순서, label 값 `0/1/2`만 포함 여부를 검증한다.
8. RunPod 재현 절차 문서를 “실제로 성공한 명령어” 기준으로 업데이트한다.

## 다른 대화와 공유할 정보

- RunPod 프로젝트 경로는 `/workspace/multimodal-bias`다.
- 사용된 GPU는 NVIDIA RTX A6000 48GB이고, 확인된 driver/CUDA는 `550.127.08`/`12.4`다.
- 안정적으로 맞추려던 Python/CUDA stack은 Python `3.10.x`, CUDA `12.4`, PyTorch `2.6.0+cu124` 계열이다.
- Qwen2.5-VL용 dependency 파일은 `requirements-gpu-qwen2-5-vl-cu124.txt`다.
- Qwen model config는 `configs/models/qwen2_5_vl_7b.yaml`이고 현재 `max_new_tokens: 512`로 확인됐다.
- 기존 `multimodal-bias infer`는 transformers sequential path라서 70분 목표에 부적합하다.
- 실패를 빠르게 기록한 run과 실제 generated run의 속도를 혼동하면 안 된다.
- `20260619_041654_default`는 빠르게 끝난 것처럼 보였지만 `source_failed: 8500`이었고 제출 불가였다.
- vLLM 0.10.2 + Qwen2.5-VL-7B에서 확인된 호환 문제는 `rope_scaling`, tokenizer `all_special_tokens_extended`, image processor `min_pixels/max_pixels`, V1 engine config 처리다.
- `Gloo Rank 0 is connected to 0 peer ranks`는 단일 GPU 환경에서 치명 오류로 확인된 것은 아니다.
- `Application startup complete`가 vLLM server 기동 성공 기준이다.

## 근거 및 신뢰도

- 대화에서 직접 확인된 내용:
  - RunPod `nvidia-smi` 출력으로 A6000 48GB, Driver `550.127.08`, CUDA `12.4` 확인.
  - MiniCPM snapshot 다운로드 `17.4G/17.4G`, 23 files 완료.
  - `rsync`로 `open.zip` 2.898GB 전송 완료.
  - MiniCPM smoke-model 성공 출력.
  - Qwen HF local run의 `Invalid device string: '0'` 오류와 `source_failed: 8500` 확인.
  - Qwen HF local generated run의 약 495~536분 추정 확인.
  - vLLM Qwen server의 `rope_type/type`, `all_special_tokens_extended`, `min_pixels`, `vocab_size` 오류 로그 확인.

- 대화 내용을 바탕으로 한 해석:
  - 70분 내 전체 제출물 생성을 위해서는 HF sequential inference가 아니라 vLLM batch/server/offline 경로가 필요하다.
  - Qwen2.5-VL-7B 자체보다 현재 병목은 추론 엔진과 batch 처리 부재다.
  - vLLM V1 engine의 Qwen2.5-VL 처리 경로가 현재 환경에서 깨졌을 가능성이 높다.

- 확인되지 않은 내용:
  - `VLLM_USE_V1=0` 적용 후 vLLM server 최종 기동 성공 여부.
  - vLLM offline batch 스크립트의 실제 생성 및 실행 여부.
  - 최종 `submission.csv` 생성 여부.
  - Multimodal public LB 제출 여부와 점수.
  - private/hidden 성능.
  - RunPod 원격 파일들의 현재 실시간 상태.
