# 대화 001 - Multimodal 236722 멀티모달 Bias 검증·제출물 생성 실험 정리

## 목적

Multimodal 236722 과제에서 `Qwen/Qwen3.5-9B` 기반 프롬프트·추론 방식·해상도·모델 교체 후보를 검증하고, 검증셋 및 test 8500 full 실행 결과를 바탕으로 제출 후보 파일을 생성·수거하는 것.

## 핵심 요약

이 대화에서는 `v3.1`, `v3.2`, `v3.3`, `v3.4vis`, `v3.5`, `v3.6`, self-consistency, 1pass/2pass/3pass, 고해상도 이미지 설정을 순차적으로 실험했다.
기본 모델은 대부분 `Qwen/Qwen3.5-9B`로 고정했고, vLLM 서버를 RunPod GPU 서버에서 실행했다.
검증셋 188문항 기준으로 여러 프롬프트와 pass 구성을 A/B 채점했으며, 통과 또는 사용 가치가 있는 후보는 test 8500 full로 실행했다.
`v3.4vis`는 이미지 언급률을 올렸지만 기존 대비 disagreement가 늘었고, 고해상도 실험에서도 동일하게 기존과 차이가 커졌다.
`v3.5`, `v3.6`, `v3.1 3pass` 등 5개 후보는 test full까지 실행되어 submission과 raw, summary가 로컬로 수거되었다.
이후 `gemma4-26b-a4b-awq` 모델로 `v3.1 2pass + hires` full 실험을 준비했으나, 기존 vLLM 환경이 `gemma4` 아키텍처를 인식하지 못해 별도 vLLM 환경 설치가 진행 중이거나 확인 필요 상태로 남았다.

## 시도한 작업

시간 순서대로 정리했다.

| 순서 | 시도한 내용 | 사용한 방법·명령어 | 결과 |
| -- | ------ | ---------- | --------------- |
| 1 | 로컬 검증셋 패키지 준비 | `data/local-validation/`의 `v3_handoff_LITE.zip`, `v3_ab_handoff.zip`, `two_pass_handoff.zip` 등 사용 | 성공 |
| 2 | v3 best baseline 검증 | `run_valset.py`, `score_valset.py` | 성공 |
| 3 | v3.1 A/B 검증 | `run_valset.py --system-prompt-file ...system_v3_1_anon_guard.txt` | 성공 |
| 4 | v3.1 full 제출물 생성 | `python3 run_inference_v31_vllm.py --data-dir data/raw/open/test --output-dir runs/... --concurrency 32` | 확인되지 않음 |
| 5 | v3.2 2-pass 검증 | `python3 two_pass_v32/run_2pass_vllm.py ... reasoner_system_v32.txt ... verifier_system_v32.txt` | 성공 |
| 6 | v3.3 2-pass 검증 | `python3 two_pass_v32/run_2pass_vllm.py ... reasoner_system_v33.txt ... verifier_system_v33.txt` | 성공 |
| 7 | v3.2 / v3.3 test full 실행 | `run_2pass_vllm.py --data-dir data/raw/open/test --csv-name test.csv ...` | 일부 확인되지 않음 |
| 8 | 결과물 로컬 수거 | `scp` / SSH 기반 수거 | 성공 |
| 9 | self-consistency sc1/sc3/sc5 검증 및 게이트 | `two_pass_v32/run_2pass_sc_vllm.py --sc-n 1/3/5 --sc-temp 0.7` | 확인되지 않음 |
| 10 | v3.4vis 검증 | `run_2pass_vllm.py ... reasoner_system_v34vis.txt` | 성공 |
| 11 | v3.4vis test full | `runs/test-v34vis-20260628-0345` 생성 | 성공 |
| 12 | v3.4vis hires full | `scripts/serve_inference_14006_vllm_hires.sh`, `runs/test-v34vis-hires-20260628-0507` | 성공 |
| 13 | v3.1 hires full | `runs/test-v31-hires-20260628-0615` | 성공 |
| 14 | 7개 후보 검증셋 스크리닝 | `run_1pass_vllm.py`, `run_2pass_vllm.py`, `run_3pass_vllm.py` | 성공 |
| 15 | 5개 후보 test full | `v31-3pass`, `v36-2pass`, `v36-3pass`, `v35-2pass`, `v35-3pass` | 성공 |
| 16 | v3.1 verifier 제거 1pass full | `run_1pass_vllm.py --no-verify` | 중단 또는 확인 필요 |
| 17 | Gemma4 AWQ 모델 다운로드 | `huggingface-cli download cyankiwi/gemma-4-26B-it-AWQ-4bit` 또는 `huggingface-cli download cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit` 관련 작업 | 성공 |
| 18 | Gemma4 AWQ vLLM 서버 실행 시도 | 기존 `.venv-vllm-0171` 사용 | 실패 |
| 19 | Gemma4용 vLLM 0.20 환경 설치 | `.venv-vllm-gemma4`, `pip install vllm==0.20.0` | 부분 성공 |
| 20 | CUDA 12.9용 vLLM 환경 재설치 시도 | `torch==2.11.0` cu129 + `vllm-0.20.0+cu129` wheel | 진행 상태 확인 필요 |

## 성공한 내용

RunPod 서버에서 Qwen3.5-9B 기반 vLLM 추론을 여러 차례 수행했다.

`v3.4vis` low-res full 결과가 생성되었다.

- 경로: `runs/test-v34vis-20260628-0345`
- rows: `8500`
- labels: `[0,1,2]`
- nulls: `0`
- seconds: `2264.0474`
- seconds_per_sample: `0.26636`
- 기존 0.99617 대비 disagreement: `233`
- 이미지 언급률: `2238/8500 = 26.3%`

`v3.4vis-hires` full 결과가 생성되었다.

- 경로: `runs/test-v34vis-hires-20260628-0507`
- rows: `8500`
- labels: `[0,1,2]`
- nulls: `0`
- seconds: `2736.6247`
- seconds_per_sample: `0.32196`
- 기존 v3.1 대비 disagreement: `281`
- 저해상도 v3.4vis 대비 disagreement: `200`
- 이미지 언급률: `2530/8500 = 29.8%`

`v3.1-hires` full 결과가 생성되었다.

- 경로: `runs/test-v31-hires-20260628-0615`
- rows: `8500`
- labels: `[0,1,2]`
- nulls: `0`
- seconds: `2514.3461`
- seconds_per_sample: `0.29581`
- v3.1 저해상도 대비 disagreement: `231`
- 이미지 언급률: `1588/8500 = 18.7%`

7개 후보 검증셋 스크리닝이 완료되었다.

| 후보 | Balanced | amb_protected | amb_gender | dis_named | dis_protected |
| -- | --: | --: | --: | --: | --: |
| baseline v3.1 2pass | 0.7689 | 0.420 | 0.650 | 0.896 | 1.000 |
| v3.1 1pass | 0.7472 | 0.400 | 0.600 | 0.875 | 1.000 |
| v3.1 3pass | 0.8125 | 0.620 | 0.500 | 0.938 | 1.000 |
| v3.6 1pass | 0.7954 | 0.560 | 0.500 | 0.979 | 0.944 |
| v3.6 2pass | 0.8060 | 0.580 | 0.500 | 1.000 | 0.944 |
| v3.6 3pass | 0.8005 | 0.580 | 0.450 | 1.000 | 0.944 |
| v3.5 2pass | 0.8365 | 0.780 | 0.500 | 0.896 | 0.944 |
| v3.5 3pass | 0.8421 | 0.800 | 0.500 | 0.896 | 0.944 |

5개 후보 test full이 완료되고 로컬로 수거되었다.

| 후보 | 경로 | rows | nulls | seconds_per_sample | 분 | 기존 대비 disagreement | 이미지 언급률 |
| -- | -- | --: | --: | --: | --: | --: | --: |
| v3.1 3pass | `runs/test-v31-3pass-0628-1639` | 8500 | 0 | 0.240819830 | 34.116 | 238 | 16.318% |
| v3.6 2pass | `runs/test-v36-2pass-0628-1714` | 8500 | 0 | 0.190009147 | 26.918 | 451 | 38.212% |
| v3.6 3pass | `runs/test-v36-3pass-0628-1743` | 8500 | 0 | 0.195780641 | 27.736 | 404 | 38.612% |
| v3.5 2pass | `runs/test-v35-2pass-0628-1812` | 8500 | 0 | 0.266601858 | 37.769 | 334 | 34.224% |
| v3.5 3pass | `runs/test-v35-3pass-0628-1851` | 8500 | 0 | 0.274002475 | 38.817 | 347 | 34.529% |

Gemma4 AWQ 모델 파일 다운로드 자체는 완료되었다.

- 원격 경로: `/workspace/multimodal-14006-repro/model/gemma4-26b-a4b-awq`
- 모델 ID로 확인된 값: `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`

## 실패하거나 중단된 내용

- 로컬에서 `rsync`를 사용한 업로드가 실패했다.
- 기존 vLLM 0.17.1 환경에서 Gemma4 AWQ 모델 실행이 실패했다.
- Gemma4용 vLLM 0.20.0 설치 후 기본 설치된 Torch CUDA 13.0 계열이 서버 NVIDIA 드라이버와 맞지 않아 CUDA 사용이 실패했다.
- `v3.1 verifier 제거 1pass full` 작업은 시작 또는 재시작 정황은 있으나 최종 완료 여부가 확인되지 않는다.
- self-consistency sc1/sc3/sc5 작업은 사용자가 이어서 진행하라고 했으나 최종 산출 결과는 이 대화 요약 기준 확인되지 않는다.

## 발생한 오류와 원인

오류 메시지가 있다면 핵심 부분을 포함하고, 확인된 원인과 추정 원인을 구분했다.

| 오류 | 핵심 메시지 | 확인된 원인 | 추정 원인 |
| -- | -- | -- | -- |
| `rsync` 실패 | `bash: line 1: rsync: command not found` | 로컬 또는 실행 환경에 `rsync` 없음 | 해당 없음 |
| Qwen 추론 중 tokenizer 오류 | `Already borrowed` | `TOKENIZERS_PARALLELISM=false` 미설정 시 tokenizer 병렬 접근 문제 발생 | 고동시성 요청에서 tokenizer 내부 borrow 충돌 |
| Gemma4 vLLM 0.17.1 실행 실패 | `checkpoint has model type gemma4 but Transformers does not recognize this architecture` | 기존 vLLM/Transformers가 `gemma4` 아키텍처 미지원 | 최신 Transformers/vLLM 필요 |
| Gemma4 vLLM 0.20 설치 후 CUDA 실패 | `NVIDIA driver ... too old`, `torch.cuda.is_available() False` | 설치된 Torch가 CUDA 13.0 빌드였고 서버 드라이버가 부족 | CUDA 12.9 계열 Torch/vLLM wheel 필요 |

## 결정사항

- 기본 실험 모델은 `Qwen/Qwen3.5-9B`로 고정했다.
- 기존 기준 제출물은 `runs/test-2pass-20260624-1225/submission.csv`이며 Public `0.99617` 기준으로 비교했다.
- 저해상도 기본 이미지 설정은 `max_pixels=200704`, `min_pixels=50176`이다.
- 고해상도 실험은 `max_pixels=451584`를 사용했다.
- vLLM 서버 실행 시 tokenizer 오류 방지를 위해 `TOKENIZERS_PARALLELISM=false`가 필요하다.
- 검증셋 게이트 없이 test full을 돌리지 않는 원칙이 여러 작업에서 적용되었으나, 사용자가 “Private 베팅”으로 명시한 `v3.4vis`는 검증셋 하락에도 test full을 실행했다.
- 리더보드 제출은 직접 하지 않고 submission 파일만 생성하는 것으로 유지했다.
- Gemma4 AWQ 실험은 별도 vLLM 0.20 계열 환경이 필요하다.

## 변경된 파일

| 파일 경로 | 변경 유형 | 변경 내용 | 현재 상태 |
| ----- | ----------------- | ----- | ---------- |
| `runs/test-v34vis-20260628-0345/` | 생성 / 이동 | 원격 full 결과 수거 | 완료 |
| `runs/test-v34vis-hires-20260628-0507/` | 생성 / 이동 | 원격 hires full 결과 수거 | 완료 |
| `runs/test-v31-hires-20260628-0615/` | 생성 / 이동 | 원격 v3.1 hires full 결과 수거 | 완료 |
| `runs/test-v31-3pass-0628-1639/` | 생성 / 이동 | 5개 후보 full 결과 수거 | 완료 |
| `runs/test-v36-2pass-0628-1714/` | 생성 / 이동 | 5개 후보 full 결과 수거 | 완료 |
| `runs/test-v36-3pass-0628-1743/` | 생성 / 이동 | 5개 후보 full 결과 수거 | 완료 |
| `runs/test-v35-2pass-0628-1812/` | 생성 / 이동 | 5개 후보 full 결과 수거 | 완료 |
| `runs/test-v35-3pass-0628-1851/` | 생성 / 이동 | 5개 후보 full 결과 수거 | 완료 |
| `/workspace/multimodal-14006-repro/model/gemma4-26b-a4b-awq` | 생성 | Gemma4 AWQ 모델 다운로드 | 완료 |
| `/workspace/multimodal-14006-repro/.venv-vllm-gemma4` | 생성 / 수정 | Gemma4 실행용 vLLM 환경 설치 | 확인 필요 |

## 현재 상태

부분 완료.

Qwen 기반 검증셋 및 여러 test full 실험은 상당 부분 완료되었고, 주요 submission 결과도 로컬로 수거되었다.
다만 현재 마지막 작업인 `gemma4-26b-a4b-awq` 기반 `v3.1 2pass + hires` full 제출물 생성은 모델 다운로드 이후 vLLM/Torch/CUDA 호환성 문제 때문에 완료되지 않았으며, CUDA 12.9 계열 환경 재설치 상태 확인이 필요하다.

## 미해결 사항

- Gemma4 AWQ 모델을 RunPod 서버에서 vLLM으로 정상 serve할 수 있는지 확인 필요.
- `/workspace/multimodal-14006-repro/.venv-vllm-gemma4`의 CUDA 12.9 재설치가 완료되었는지 확인 필요.
- Gemma4 full 결과 `submission.csv` 생성 여부는 확인되지 않음.
- `v3.1 verifier 제거 1pass full` 최종 결과는 확인되지 않음.
- self-consistency sc1/sc3/sc5 최종 결과는 확인되지 않음.
- 실제 Multimodal 리더보드 제출 결과는 대화 내에서 확인되지 않음.

## 다음 작업

1. RunPod 서버에서 Gemma4용 vLLM 환경 설치 상태를 확인한다.
2. CUDA 사용 가능 여부를 확인한 뒤 Gemma4 AWQ를 `max_pixels=451584`로 serve한다.
3. `v3.1 2pass + hires + gemma4-26b-a4b-awq` full 실행 후 `submission.csv`, `raw.jsonl`, `summary.json`을 검증하고 로컬로 수거한다.
4. 기존 `0.99617` 기준 submission과 disagreement, unknown율, 이미지 언급률을 비교한다.
5. 확인되지 않은 `v3.1 1pass no-verifier` 및 self-consistency 결과가 필요한지 별도 확인한다.

## 다른 대화와 공유할 정보

- 원격 서버 접속 정보는 공개 저장소에 포함하지 않도록 비식별화함.
- 실제 호스트·포트·사용자명·키 경로는 로컬 비공개 기록에서만 관리.
- 원격 레포 경로:
  - `/workspace/multimodal-bias`
- 기존 기준 제출물:
  - `/workspace/multimodal-bias/runs/test-2pass-20260624-1225/submission.csv`
- Qwen 모델 경로:
  - `/workspace/multimodal-14006-repro/model/Qwen3.5-9B`
- Gemma4 AWQ 모델 경로:
  - `/workspace/multimodal-14006-repro/model/gemma4-26b-a4b-awq`
- Gemma4 모델 ID:
  - `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`
- Gemma4는 기존 vLLM 0.17.1 환경에서 실행 불가.
- Gemma4 실행에는 최신 Transformers/vLLM이 필요하고, RunPod 드라이버 호환 때문에 CUDA 13.0이 아니라 CUDA 12.9 계열이 필요했다.
- Qwen vLLM 실행 시 `TOKENIZERS_PARALLELISM=false`를 설정해야 tokenizer `Already borrowed` 오류를 피할 수 있다.
- 리더보드 제출은 하지 않고 submission 파일만 생성하는 원칙이 유지되었다.

## 근거 및 신뢰도

- 대화에서 직접 확인된 내용:
  - 사용자가 제공한 실행 지시, SSH 정보, 금지사항, 프롬프트 파일명, 데이터 경로, 실행 명령어.
  - Qwen 기반 여러 full 결과의 rows/nulls/summary/disagreement/이미지 언급률.
  - Gemma4 모델 다운로드 완료 및 vLLM 0.17.1 실행 실패.
  - CUDA 13.0 Torch와 서버 드라이버 불일치 오류.

- 대화 내용을 바탕으로 한 해석:
  - `v3.4vis`와 hires 실험은 이미지 활용률을 높이려는 목적이었지만 기존 Public 기준과의 disagreement가 증가했다.
  - Gemma4 작업은 모델 자체보다 vLLM/Transformers/Torch/CUDA 호환성 문제가 주된 blocker다.

- 확인되지 않은 내용:
  - v3.1 full `run_inference_v31_vllm.py`의 최종 생성물과 리더보드 결과.
  - self-consistency sc1/sc3/sc5 최종 채점표.
  - v3.1 no-verifier 1pass full 최종 결과.
  - Gemma4 CUDA 12.9 환경 재설치 완료 여부.
  - Gemma4 full submission 생성 여부.
  - 실제 Multimodal 제출 및 점수.
