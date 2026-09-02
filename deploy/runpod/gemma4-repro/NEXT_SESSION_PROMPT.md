# 새 Codex 대화에 붙여넣을 프롬프트

아래 코드 블록 전체를 새 대화의 첫 메시지로 붙여넣으세요.

```text
나는 Multimodal 236722 멀티모달 AI Bias 평가 실험을 새 RunPod RTX A6000 인스턴스에서 이어서 진행한다. 설명만 하지 말고 SSH 연결 상태와 파일을 직접 확인하면서 단계별로 실행하라. 기존 파일이나 run을 삭제·덮어쓰지 말고, 비싼 Full 실행 전에는 환경·서버·실데이터 smoke 검증을 반드시 통과시켜라.

현재 검증된 최고 기준선:
- 모델: cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit
- revision: 4033b16200f4152e55e100ea12dc388c537df622
- Reasoner SHA-256: 87d694d0b968ccef4606a979f52c5de63454e870be71a6d9f4e91ef942067cb6
- Reasoner: configs/prompts/reasoner_v3.yaml, 변경 금지
- Public: 0.9634, 당시 순위 83등
- Full: 8,500/8,500 유효, failure/parse invalid/retry 0건
- 실행시간: 2506.961842초(41분 47초), concurrency 32
- initial max tokens 256, invalid만 512 재시도
- predictions SHA-256: 09b81b6309c383dd5f0cea1f2579eb4cb93d152d6356d536a7f076c46e4add45

검증된 RunPod 환경:
- Ubuntu 24.04.3 LTS
- NVIDIA RTX A6000 48GB, driver 550.127.08
- Python 3.12 venv: /workspace/gemma4-vllm-cu129
- torch 2.11.0+cu129 / CUDA 12.9
- vLLM 0.23.0+cu129
- transformers 5.12.1
- openai 2.43.0
- fastapi 0.116.1
- starlette 0.47.3
- prometheus-fastapi-instrumentator 7.1.0
- ninja 1.13.0

로컬에서 새 Pod로 가져갈 파일:
1. runpod-gemma4-repro-20260621-gemma26.tar.gz
2. runpod-gemma4-repro-20260621-gemma26.tar.gz.sha256
3. open.zip (또는 이미 풀린 data/raw/open 전체)

기본 원격 경로:
- 프로젝트: /workspace/multimodal-bias
- 번들: /workspace/multimodal-bias/runpod-gemma4-repro
- 데이터: /workspace/multimodal-bias/data/raw/open
- 모델: /workspace/multimodal-bias/models/snapshots/Gemma4-26B-A4B-it-AWQ-4bit
- runs: /workspace/multimodal-bias/runs

먼저 다음을 확인하라:
1. `nvidia-smi`로 GPU/driver 확인
2. `df -h /workspace`로 최소 45GiB 여유 확인
3. 전송된 archive checksum 확인 후 압축 해제
4. open.zip을 data/raw/open에 풀고 test image가 정확히 8,500개인지 확인
5. 기존 venv/model/run이 있으면 revision과 버전을 검사하고 일치할 때만 재사용

환경은 임의 설치하지 말고 번들로 구성한다:
```
cd /workspace/multimodal-bias/runpod-gemma4-repro
chmod +x ./*.sh profiles/*.sh
export GEMMA_PROFILE=gemma4-26b-a4b-awq
export WORKSPACE_ROOT=/workspace/multimodal-bias
export DATA_ROOT=/workspace/multimodal-bias/data/raw/open
export VENV_DIR=/workspace/gemma4-vllm-cu129
./bootstrap.sh
```

bootstrap은 Python 3.12 venv를 만들고 requirements-critical.txt를 설치해야 한다. 핵심 설치물은 CUDA 12.9용 vLLM 0.23.0 wheel, torch/vision/audio 2.11/0.26 cu129, transformers 5.12.1, openai 2.43.0, PyYAML 6.0.3, fastapi 0.116.1, starlette 0.47.3, instrumentator 7.1.0, ninja 1.13.0이다. `verify_environment.py`가 전부 일치하는지 확인해야 한다.

그다음 순서:
```
./download_model.sh
./serve.sh
curl -i http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/v1/models
./smoke.sh
```

vLLM은 반드시 127.0.0.1:8000, TP=1, max-model-len=32768, gpu-memory-utilization=0.90, generation-config=vllm로 실행한다. health는 HTTP 200이어야 하고 `/v1/models`에 정확한 모델 ID가 있어야 한다. `libcudart.so.13`, ninja, HTTP 500 문제가 나면 다른 버전으로 우회하지 말고 번들의 고정 wheel/PATH/FastAPI 호환 핀을 확인하라.

smoke는 1건과 50건 c32를 실행한다. 50/50 유효, failure 0, parse invalid 0을 확인한 후에만 Full 실행을 제안하라. Full 승인 시:
```
RUN_ID=gemma4_26b_a4b_awq_v3_full_c32_$(date -u +%Y%m%dT%H%M%SZ) ./run_full.sh
```

완료 후 summary.json에서 8,500/8,500, 오류 0, runtime을 확인하고 submission.csv 경로와 SHA-256을 보고하라. 모델과 Reasoner를 한 실험에서 동시에 변경하지 말고, 모든 새 후보는 별도 run 디렉터리와 정확한 revision을 남겨라.
```
