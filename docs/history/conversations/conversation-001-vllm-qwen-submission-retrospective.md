# 대화 001 - vLLM 기반 Qwen2.5-VL 제출 생성 및 0.91 점수 원인 조사

## 목적

Multimodal 236722 멀티모달 AI Bias 과제에서 Hugging Face 경로가 느리고 성능도 만족스럽지 않다는 문제를 해결하기 위해, RunPod에 연결된 VSCode 환경을 활용하여 반드시 vLLM 기반으로 추론을 수행하고 70분 제한 안에서 제출용 `submission.csv`를 생성하는 것이 목표였다.

추가로, 생성된 제출물이 0.91점을 받은 뒤 어디에서 문제가 있었는지 확인하고, 이후 GitHub 프로젝트 정리에 필요한 실행 기록, 오류, 변경사항, 미해결 과제를 남기는 것이 목표였다.

## 핵심 요약

사용자는 Hugging Face 기반 추론이 느리고 성능도 좋지 않으므로 vLLM으로 진행하라고 명시했다. RunPod 원격 환경에서 Qwen2.5-VL-7B-Instruct 모델을 vLLM 서버로 띄우려 했으나, 초기에는 vLLM의 Qwen2.5-VL 설정 호환성 문제로 서버가 정상 기동하지 않았다. `Qwen2_5_VLConfig`와 `Qwen2_5_VLTextConfig` 관련 오류를 처리하기 위해 vLLM 설치 경로의 모델 구현을 패치했고, 최종적으로 vLLM 서버를 띄운 뒤 8,500개 테스트 샘플에 대한 제출 파일을 생성했다. 최종 제출물은 원격 기준 `/workspace/multimodal-bias/runs/20260619_061802_default/submission.csv`였고, 로컬에는 `/Users/gongman/Desktop/퀸2.5 1/submission.csv`로 확인되었다. 해당 CSV는 헤더 포함 8,501행, 예측 8,500개이며 SHA256은 `c1a00048f69955048142f1cedb1141f759dc325006d276725120c5c5e4d7f04c`로 확인되었다. 실행 시간은 전체 산출물 생성 기준 약 65분 20초로, 사용자가 요구한 70분 제한 이내이면서 60분대 실행 조건을 만족했다. 이후 사용자가 제출 평가 결과 0.91점을 공유했고, 조사 결과 가장 강한 원인은 프롬프트가 “불확실성 = label 2”로 하드코딩되어 있었던 점으로 정리되었다. Multimodal의 label은 선택지의 0-based 인덱스인데, 테스트셋에서는 불확실성 선택지 위치가 0, 1, 2로 섞여 있었으므로 label 2를 의미 클래스처럼 다룬 것이 제출 품질을 크게 훼손했을 가능성이 높다. 다만 RunPod 연결이 끊기고 raw output/server log가 소실되어, 각 샘플별 모델 응답과 정확한 오답 원인 분해는 확인할 수 없다.

## 시도한 작업

시간 순서대로 정리했다.

| 순서 | 시도한 내용 | 사용한 방법·명령어 | 결과 |
| -- | ------ | ---------- | --------------- |
| 1 | Hugging Face 대신 vLLM을 사용해야 한다는 실행 방향 확정 | 사용자 지시: “반드시 vllm에서 진행할 것”, “hf로 하면 성능도 안 좋고 속도도 느린데 왜 hf로 하나” | 성공 |
| 2 | RunPod 원격 프로젝트 경로로 이동하고 vLLM 가상환경 활성화 | `cd /workspace/multimodal-bias`, `source /workspace/vllm-minicpm/bin/activate` | 성공 |
| 3 | 기존 vLLM/EngineCore 프로세스 정리 | `pkill -f "vllm serve" || true`, `pkill -f "EngineCore" || true` | 성공 |
| 4 | vLLM Qwen2-VL image processor min/max pixel fallback 패치 | Python으로 `/workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/model_executor/models/qwen2_vl.py` 수정 | 성공 |
| 5 | qwen2_vl.py 패치 확인 | `grep -n "min_pixels=getattr\\|max_pixels=getattr" /workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/model_executor/models/qwen2_vl.py` | 성공, 865-866행에 fallback 확인 |
| 6 | vLLM 서버 1차 기동 시도 | `nohup vllm serve ... --max-model-len 4096 --mm-processor-kwargs '{"min_pixels":200704,"max_pixels":602112}' > /workspace/qwen_vllm.log 2>&1 &`, `tail -f /workspace/qwen_vllm.log` | 실패 |
| 7 | vLLM 서버 1차 오류 확인 | `/workspace/qwen_vllm.log` 확인 | 실패 원인 확인: `Qwen2_5_VLConfig`에 `vocab_size` 없음 |
| 8 | Qwen2.5-VL vLLM 모델 구현에서 text_config 전달 패치 | Python으로 `/workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/model_executor/models/qwen2_5_vl.py` 수정 | 부분 성공 |
| 9 | vLLM 서버 2차 기동 시도 | `nohup vllm serve ... --max-model-len 8192 --mm-processor-kwargs '{"min_pixels":200704,"max_pixels":602112}' > /workspace/qwen_vllm.log 2>&1 &`, `tail -f /workspace/qwen_vllm.log` | 실패 |
| 10 | vLLM 서버 2차 오류 확인 | `/workspace/qwen_vllm.log` 확인 | 실패 원인 확인: `Qwen2_5_VLTextConfig`에 `tie_word_embeddings` 없음 |
| 11 | Qwen2.5-VL vLLM 모델 구현에 tie_word_embeddings fallback 추가 | 대화 기록상 `qwen2_5_vl.py`에 fallback 적용 | 성공으로 기록됨, 전체 diff는 현재 확인 불가 |
| 12 | Prometheus FastAPI Instrumentator route 호환성 문제 처리 | `/workspace/vllm-minicpm/lib/python3.10/site-packages/prometheus_fastapi_instrumentator/routing.py`에서 `.path` 없는 route skip 패치 | 성공으로 기록됨, 원격 파일 현재 확인 불가 |
| 13 | 모델 설정 호환성 처리 | 모델 config에서 `rope_scaling.type`을 `rope_type: "mrope"`로 변경 | 성공으로 기록됨, 원격 파일 현재 확인 불가 |
| 14 | 전처리 pixel 설정 조정 | preprocessor 설정 min/max pixels를 `200704/602112`로 조정 | 성공으로 기록됨, 원격 파일 현재 확인 불가 |
| 15 | vLLM 서버 상태 확인 시도 | `curl -s http://127.0.0.1:8000/v1/models \| python -m json.tool` | 실패 시점 존재: `Expecting value: line 1 column 1 (char 0)` |
| 16 | 최종 vLLM 서버 실행 | `/workspace/vllm-minicpm/bin/vllm serve /workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct --trust-remote-code --dtype bfloat16 --host 127.0.0.1 --port 8000 --served-model-name Qwen/Qwen2.5-VL-7B-Instruct --gpu-memory-utilization 0.90 --max-model-len 8192 --mm-processor-kwargs '{"min_pixels":200704,"max_pixels":602112}'` | 성공 |
| 17 | vLLM API 기반 추론 실행 | `/workspace/vllm_reasoner_runner.py` 사용, `httpx`로 `http://127.0.0.1:8000/v1/chat/completions` 호출, concurrency 8, `temperature=0`, `max_tokens=256`, retries 3 | 성공 |
| 18 | 제출 파일 생성 | `/workspace/multimodal-bias/runs/20260619_061802_default/submission.csv` 생성 | 성공 |
| 19 | 제출 파일이 다운로드 대상인지 확인 | 사용자 질문: “이것만 다운 하면 돼?”에 대해 `submission.csv`가 제출 대상이라고 정리 | 성공 |
| 20 | 최종 제출 파일 로컬 위치 확인 | `find /Users/gongman -type f \( -name 'submission.csv' -o -name '*submission*.csv' \) -mtime -2 -print` | 성공: `/Users/gongman/Desktop/퀸2.5 1/submission.csv` 확인 |
| 21 | 제출 파일 해시 확인 | `shasum -a 256 '/Users/gongman/Desktop/퀸2.5 1/submission.csv'` | 성공: `c1a00048f69955048142f1cedb1141f759dc325006d276725120c5c5e4d7f04c` |
| 22 | 제출 파일 행 수 및 예측 수 확인 | CSV 검사 | 성공: 8,501행, 예측 8,500개 |
| 23 | 실행 시간 정리 | 서버 기동, ready, calibration, full run 시간 기록 정리 | 성공: 약 65분 20초 |
| 24 | 사용 라이브러리와 vLLM 실행 환경 정리 | 원격 환경에서 확인된 버전 기록 정리 | 성공 |
| 25 | 제출 점수 0.91 원인 조사 | 로컬 `submission.csv`, `data/raw/open/test/test.csv`, 프롬프트/파서/제출 코드 확인 | 부분 성공 |
| 26 | 불확실성 선택지 위치 분포 확인 | Python 분석: 테스트셋 answers에서 uncertainty option 위치 산출 | 성공: position 0 = 3050, 1 = 2718, 2 = 2732 |
| 27 | 예측 label과 uncertainty 위치 교차 분석 | Python 분석: 제출 label과 uncertainty option index 교차표 계산 | 성공: 불확실성 옵션 선택률 전체 56.34% |
| 28 | 프롬프트 label 의미 버그 확인 | `configs/prompts/reasoner_v1.yaml`, `src/multimodal_bias/prompting/templates.py`, `src/multimodal_bias/parsing.py`, `src/multimodal_bias/submission.py` 확인 | 성공 |
| 29 | 조사 문서 생성/수정 | `/Applications/학교 외부/멀티모달 AI Bias/experiments/investigations/submission-score-091-investigation.md` 작성 및 정정 | 성공 |
| 30 | BMad 도움말 확인 | `sed -n '1,320p' /Users/gongman/.agents/skills/bmad-help/SKILL.md`, `/Users/gongman/_bmad/_config/bmad-help.csv` 확인 | 성공 |
| 31 | GitHub 프로젝트 정리용 문서 생성 | 이 파일 `/Applications/학교 외부/멀티모달 AI Bias/docs/conversation-001-vllm-qwen-submission-retrospective.md` 생성 | 성공 |

## 성공한 내용

- RunPod 원격 환경에서 vLLM 기반 추론이 최종적으로 실행되었다.
- Qwen2.5-VL-7B-Instruct 모델을 vLLM 서버로 띄우는 데 필요한 호환성 패치가 적용되었다.
- 최종 제출 파일 `/workspace/multimodal-bias/runs/20260619_061802_default/submission.csv`가 생성되었다.
- 로컬 다운로드 파일 `/Users/gongman/Desktop/퀸2.5 1/submission.csv`가 확인되었다.
- 제출 파일은 헤더 포함 8,501행, 예측 8,500개로 확인되었다.
- 제출 파일 SHA256은 `c1a00048f69955048142f1cedb1141f759dc325006d276725120c5c5e4d7f04c`로 확인되었다.
- 전체 산출물 생성 기준 약 65분 20초로, 70분 제한을 넘기지 않았고 60분대 실행 조건을 만족했다.
- vLLM 추론 자체에는 no parse failures, no retries, no fallback으로 기록되었다.
- 0.91점의 주요 원인 후보로 label 의미 정의 오류가 확인되었다.
- 대화 중 생성된 조사 문서가 `experiments/investigations/submission-score-091-investigation.md`에 남았다.

## 실패하거나 중단된 내용

- 초기 vLLM 서버 기동은 실패했다.
- `/v1/models` 확인 시 API 응답이 JSON이 아니어서 `python -m json.tool`이 실패한 시점이 있었다.
- RunPod 연결이 끊긴 뒤 원격 서버 로그, raw output, 실제 요청/응답 기록은 복구할 수 없는 상태가 되었다.
- 제출 점수 0.91의 샘플별 정확한 오답 원인은 raw output과 hidden label이 없어서 확정하지 못했다.
- 기존 제출 CSV만으로는 모델이 실제로 어떤 reasoning으로 label을 선택했는지 복구할 수 없다.
- 이미 생성된 제출 CSV를 사후 보정하는 접근은 신뢰할 수 없고, 평가 규칙상 적절성도 확인되지 않았다.
- verifier/arbitration 쪽에도 label 2를 uncertainty로 보는 코드/프롬프트가 남아 있을 수 있으나, 이 대화에서 전체 수정 완료 여부는 확인되지 않았다.

## 발생한 오류와 원인

| 오류 메시지 또는 증상 | 확인된 원인 | 추정 원인 |
| --- | --- | --- |
| `Expecting value: line 1 column 1 (char 0)` | `curl -s http://127.0.0.1:8000/v1/models` 결과가 JSON이 아니었다. | vLLM 서버가 아직 ready가 아니었거나, 직전 EngineCore 실패로 API가 정상 응답하지 않았을 가능성이 높다. |
| `AttributeError: 'Qwen2_5_VLConfig' object has no attribute 'vocab_size'` | vLLM의 Qwen2 언어 모델 초기화가 전체 VL config를 받아 `vocab_size`를 찾으려 했다. | Qwen2.5-VL config 구조와 해당 vLLM 버전의 모델 초기화 코드 간 호환성 문제다. |
| `AttributeError: 'Qwen2_5_VLTextConfig' object has no attribute 'tie_word_embeddings'` | text config를 넘긴 뒤에도 vLLM Qwen2 코드가 `tie_word_embeddings` 속성을 요구했다. | Transformers/Qwen2.5-VL text config와 vLLM 0.10.2 기대 필드가 맞지 않았다. |
| `RuntimeError: Engine core initialization failed. See root cause above. Failed core proc(s): {}` | EngineCore가 모델 로딩 중 AttributeError로 실패했다. | 위의 config 호환성 오류가 상위 RuntimeError로 전파되었다. |
| `FlashInfer is not available. Falling back to the PyTorch-native implementation...` | FlashInfer가 설치되어 있지 않았다. | 성능 경고로 보이며, 대화 기록상 서버 실패의 직접 원인으로 확인되지는 않았다. |
| `The sequence length (4096) is smaller than the pre-defined worst-case total number of multimodal tokens (4374)` | `--max-model-len 4096`이 multimodal worst-case token 수보다 작았다. | 일부 입력 실패 가능성을 줄이기 위해 최종 실행에서는 `--max-model-len 8192`로 조정했다. |
| 제출 점수 0.91 | 프롬프트가 “불확실성 = label 2”라고 지시한 것이 확인되었다. | Qwen2.5-VL-7B 모델 한계, no verifier, 이미지 pixel cap, 보수적 프롬프트도 영향을 줬을 수 있으나 raw output이 없어 효과량은 확인되지 않았다. |

## 결정사항

- 최종 추론은 Hugging Face가 아니라 vLLM으로 수행한다.
- 모델은 `/workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct`의 Qwen2.5-VL-7B-Instruct를 사용한다.
- vLLM served model name은 `Qwen/Qwen2.5-VL-7B-Instruct`로 둔다.
- vLLM 서버는 `127.0.0.1:8000`에서 OpenAI-compatible API로 사용한다.
- 최종 제출 대상 파일은 `submission.csv` 하나다.
- 최종 원격 제출 파일 경로는 `/workspace/multimodal-bias/runs/20260619_061802_default/submission.csv`다.
- 로컬에서 확인된 다운로드 파일은 `/Users/gongman/Desktop/퀸2.5 1/submission.csv`다.
- 70분 제한을 넘기지 않고, 전체 실행 시간을 60분대로 맞추는 방향이 사용자의 요구사항으로 확정되었다.
- 0.91점 원인 조사에서 우선 수정해야 할 1순위는 “label 2 = uncertainty” 하드코딩 제거다.
- 다음 실행에서는 raw output, prompt hash, image hash, engine metadata를 persistent volume에 남겨야 한다.
- RunPod ephemeral storage만 믿으면 연결 종료/Pod 삭제 이후 장애 분석이 불가능하다는 점이 확정되었다.

## 변경된 파일

| 파일 경로 | 변경 유형 | 변경 내용 | 현재 상태 |
| ----- | ----------------- | ----- | ---------- |
| `/workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/model_executor/models/qwen2_vl.py` | 수정 | `min_pixels`/`max_pixels`를 `getattr(image_processor, ..., fallback)`로 처리 | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/model_executor/models/qwen2_vl.py.bak.min_pixels` | 생성 | qwen2_vl.py 패치 전 백업 | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/model_executor/models/qwen2_5_vl.py` | 수정 | Qwen2 언어 모델 초기화에 `text_config`를 넘기고, `tie_word_embeddings` fallback을 둔 것으로 기록됨 | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/vllm-minicpm/lib/python3.10/site-packages/vllm/model_executor/models/qwen2_5_vl.py.bak.text_config` | 생성 | qwen2_5_vl.py 패치 전 백업 | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/vllm-minicpm/lib/python3.10/site-packages/prometheus_fastapi_instrumentator/routing.py` | 수정 | `.path` 없는 route 객체를 skip하도록 패치한 것으로 기록됨 | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct/config.json` | 수정 | `rope_scaling.type`을 `rope_type: "mrope"`로 바꾼 것으로 기록됨 | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct/preprocessor_config.json` | 수정 | min/max pixels를 `200704/602112`로 조정한 것으로 기록됨 | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/qwen_vllm.log` | 생성 | vLLM 서버 로그 | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/vllm_reasoner_runner.py` | 생성 | vLLM OpenAI-compatible API 호출용 추론 runner | 원격 RunPod 소실로 현재 확인 필요 |
| `/workspace/multimodal-bias/runs/20260619_061802_default/submission.csv` | 생성 | 최종 Multimodal 제출 CSV | 원격 RunPod 소실로 현재 확인 필요 |
| `/Users/gongman/Desktop/퀸2.5 1/submission.csv` | 생성 | 사용자가 다운로드한 최종 제출 CSV로 확인됨 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/experiments/investigations/submission-score-091-investigation.md` | 생성 / 수정 | 0.91 점수 원인 조사 문서 작성 및 RunPod raw output 소실 사실 반영 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/docs/conversation-001-vllm-qwen-submission-retrospective.md` | 생성 | 이 대화의 GitHub 프로젝트 정리용 문서 | 완료 |

## 현재 상태

부분 완료

vLLM 기반 최종 제출 파일 생성과 제출용 파일 확인은 완료되었다. 제출 파일의 행 수, 예측 수, 해시, 로컬 위치도 확인되었다. 다만 제출 점수는 사용자가 공유한 평가 기준으로 0.91점이었고, raw output/server log가 RunPod 연결 종료 후 소실되어 샘플별 오답 원인은 확정할 수 없다. 정적 분석상 “불확실성 = label 2” 프롬프트/계약 버그는 확인되었지만, 이 버그 하나가 0.91 전체 하락분을 얼마나 설명하는지는 확인되지 않았다.

## 미해결 사항

- RunPod 원격 환경의 최종 raw output, vLLM server log, 실제 request/response payload는 현재 확인되지 않음.
- hidden test 정답은 확인되지 않음.
- 0.91점의 샘플별 오답 유형과 class별 정확도는 확인되지 않음.
- Qwen2.5-VL-7B 자체 성능 한계가 어느 정도였는지 확인되지 않음.
- 이미지 전처리 pixel cap이 점수에 미친 영향은 확인되지 않음.
- verifier/arbitration 단계의 label 2 uncertainty 해석 문제가 전체적으로 수정되었는지는 확인되지 않음.
- 기존 제출 CSV를 사후 보정했을 때 점수가 개선되는지는 확인되지 않음.
- 해당 사후 보정이 평가 규칙상 허용되는지는 확인되지 않음.

## 다음 작업

1. `reasoner_v1` 계열 프롬프트에서 “label 2 = uncertainty” 의미를 제거하고, label을 항상 answer choice의 0-based index로만 정의한다.
2. uncertainty는 label 번호가 아니라 “선택된 answer text가 불확실성 선택지인지”로 판정하도록 parser/submission/verifier/arbitration 계약을 점검한다.
3. `configs/prompts/verifier_v1.yaml`, `src/multimodal_bias/parsing.py`, `src/multimodal_bias/arbitration.py`에서 label 2를 특별 취급하는 로직을 확인하고 필요한 경우 수정한다.
4. 독립 validation set을 만들어 uncertainty 선택지 위치 0/1/2를 균등하게 배치한 뒤 A/B 테스트를 실행한다.
5. 다음 RunPod 실행은 persistent volume 아래에서 수행하고, `raw_reasoner.partial.jsonl`, prompt hash, image hash, engine metadata를 매 행 flush한다.
6. vLLM 서버 실행 명령, 패치 diff, `pip freeze`, `nvidia-smi`, `sha256sum`, label distribution을 run directory에 함께 저장한다.
7. corrected prompt로 다시 vLLM full inference를 수행한 뒤 기존 0.91 제출과 label distribution 및 uncertainty-position별 결과를 비교한다.

## 다른 대화와 공유할 정보

- 최종 제출물 원격 경로: `/workspace/multimodal-bias/runs/20260619_061802_default/submission.csv`
- 최종 제출물 로컬 경로: `/Users/gongman/Desktop/퀸2.5 1/submission.csv`
- 최종 제출물 SHA256: `c1a00048f69955048142f1cedb1141f759dc325006d276725120c5c5e4d7f04c`
- 제출 파일 구조: 헤더 포함 8,501행, 예측 8,500개
- 제출 label 분포: `2: 3190`, `0: 2661`, `1: 2649`
- 사용자 공유 평가 결과: 0.91점
- vLLM 서버 시작: 2026-06-19 15:08:42 KST
- vLLM 서버 ready: 2026-06-19 15:09:27 KST
- full run 시작: 2026-06-19 15:18:02 KST
- full generation 시간: 3358.187초, 약 55분 58초
- 처리량: 2.5311 samples/s
- 서버 설정/보정 포함 총 소요 시간: 약 65분 20초
- calibration: 64 samples, 28.042초
- parse failures/retries/fallback: 없음으로 기록됨
- RunPod/원격 OS: Ubuntu 24.04.3 LTS, kernel 5.15.0-139-generic, x86_64
- GPU: NVIDIA RTX A6000, 49140 MiB
- NVIDIA driver: 550.127.08
- CUDA: 12.8
- Python: 3.10.18
- vLLM: 0.10.2
- torch: 2.8.0+cu128
- torchvision: 0.23.0
- transformers: 5.12.1
- tokenizers: 0.22.2
- httpx: 0.28.1
- pandas: 2.3.3
- numpy: 2.2.6
- Pillow: 12.2.0
- pyyaml: 6.0.3
- safetensors: 0.8.0
- fastapi: 0.137.2
- uvicorn: 0.49.0
- prometheus-fastapi-instrumentator: 8.0.0
- starlette: 1.3.1
- pydantic: 2.13.4
- einops: 0.8.2
- 모델 snapshot: `/workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct`
- served model name: `Qwen/Qwen2.5-VL-7B-Instruct`
- 모델 architecture: `Qwen2_5_VLForConditionalGeneration`
- dtype: `bfloat16`
- 최종 vLLM 명령:

```bash
/workspace/vllm-minicpm/bin/vllm serve \
  /workspace/multimodal-bias/models/snapshots/Qwen2.5-VL-7B-Instruct \
  --trust-remote-code \
  --dtype bfloat16 \
  --host 127.0.0.1 \
  --port 8000 \
  --served-model-name Qwen/Qwen2.5-VL-7B-Instruct \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  --mm-processor-kwargs '{"min_pixels":200704,"max_pixels":602112}'
```

- 0.91점 원인으로 가장 중요한 확인 사항:

```text
configs/prompts/reasoner_v1.yaml:
Choose label 2, the uncertainty/not objectively answerable path, only when objective support is insufficient.
```

- 실제 선택지 formatter는 answer를 0, 1, 2로 붙인다.

```text
src/multimodal_bias/prompting/templates.py:
_format_answers(...) -> f"{index}. {answer}"
```

- parser/submission은 label을 재매핑하지 않고 그대로 통과시킨다.
- 테스트셋에서 uncertainty answer choice 위치는 0, 1, 2에 섞여 있었다.
- uncertainty answer choice 위치 분포: position 0 = 3050, position 1 = 2718, position 2 = 2732
- 제출 CSV와 uncertainty 위치 교차 분석상 overall uncertainty option selected = 4789/8500 = 56.34%
- label 2가 uncertainty가 아닌 행에서도 label 2 예측이 1518/5768건 있었다.
- 다음 대화에서 우선순위는 vLLM 재구축이 아니라 label contract 수정과 raw output 보존 계약이다.

## 근거 및 신뢰도

- 대화에서 직접 확인된 내용:
  - 사용자는 Hugging Face 대신 vLLM을 사용하라고 명시했다.
  - RunPod 원격 경로는 `/workspace/multimodal-bias`였다.
  - vLLM 가상환경은 `/workspace/vllm-minicpm`이었다.
  - `curl -s http://127.0.0.1:8000/v1/models | python -m json.tool` 실행 결과 `Expecting value: line 1 column 1 (char 0)` 오류가 발생했다.
  - 첨부 로그에 `Qwen2_5_VLConfig`의 `vocab_size` AttributeError와 `Qwen2_5_VLTextConfig`의 `tie_word_embeddings` AttributeError가 남아 있다.
  - 최종 제출 파일 경로로 `/workspace/multimodal-bias/runs/20260619_061802_default/submission.csv`가 언급되었다.
  - 로컬 제출 파일 `/Users/gongman/Desktop/퀸2.5 1/submission.csv`가 확인되었다.
  - 최종 제출 파일 SHA256, row count, label distribution이 확인되었다.
  - 사용자가 제출 평가 결과 0.91점을 공유했다.
  - `configs/prompts/reasoner_v1.yaml`에 label 2를 uncertainty로 고정하는 문구가 확인되었다.
  - 테스트셋 uncertainty 선택지 위치가 0/1/2로 섞여 있음이 분석되었다.
  - RunPod 연결이 끊겨 raw output과 server log가 남아 있지 않다고 사용자가 밝혔다.

- 대화 내용을 바탕으로 한 해석:
  - vLLM 초기 실패의 직접 원인은 Qwen2.5-VL config 구조와 vLLM 0.10.2 모델 구현의 호환성 문제로 보는 것이 타당하다.
  - 0.91점의 가장 중요한 원인은 label 2를 uncertainty 의미로 하드코딩한 프롬프트/계약 버그로 보는 것이 타당하다.
  - 단일 제출 CSV만으로는 샘플별 reasoning trace를 복구할 수 없으므로, 점수 하락 원인의 효과량 분해는 불가능하다.
  - 다음 실행에서는 persistent volume과 raw artifact 보존이 필수다.

- 확인되지 않은 내용:
  - hidden test 정답과 class별 정확도
  - 0.91점의 샘플별 오답 원인
  - RunPod 연결 종료 후 원격 파일의 현재 존재 여부
  - 최종 `/workspace/qwen_vllm.log` 전체 내용
  - `/workspace/vllm_reasoner_runner.py`의 전체 코드
  - vLLM 패치 파일들의 최종 diff
  - 사후 보정 CSV가 점수를 개선하는지 여부
  - 사후 보정이 평가 규칙상 허용되는지 여부
  - verifier/arbitration label 2 특별 취급 로직의 전체 수정 완료 여부
