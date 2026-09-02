# Gemma 4 RunPod 재현 번들

이 폴더는 RTX A6000 RunPod에서 검증한 Gemma 4 + Reasoner v3 환경을 재현한다. 기본 프로필은 Public `0.9634`, 8,500/8,500 유효 출력, 41분 47초를 기록한 Gemma 4 26B-A4B AWQ다. 기존 Gemma 4 12B(Public `0.9490833333`)도 별도 프로필로 보존한다.

모델 가중치, 평가 데이터, 가상환경, 토큰, SSH 키, 기존 run은 번들에 포함하지 않는다.

## 검증된 환경

- Ubuntu 24.04.3 LTS
- NVIDIA RTX A6000 48GB, driver `550.127.08`
- Python `3.12`
- Torch `2.11.0+cu129`, CUDA `12.9`
- vLLM `0.23.0+cu129`
- Transformers `5.12.1`, OpenAI `2.43.0`
- FastAPI `0.116.1`, Starlette `0.47.3`
- prometheus-fastapi-instrumentator `7.1.0`, Ninja `1.13.0`
- vLLM: `127.0.0.1:8000`, TP 1, context 32768, GPU utilization 0.90
- 검증된 Reasoner v3 SHA-256: `87d694d0b968ccef4606a979f52c5de63454e870be71a6d9f4e91ef942067cb6`
- Reasoner v3: concurrency 32, 256 tokens, invalid row만 512 tokens 재시도

## 프로필

기본 프로필:

```bash
export GEMMA_PROFILE=gemma4-26b-a4b-awq
```

- 모델: `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`
- revision: `4033b16200f4152e55e100ea12dc388c537df622`
- vLLM 추가 인자: `--generation-config vllm`
- smoke: 1건 후 50건 c32

기존 12B 프로필:

```bash
export GEMMA_PROFILE=gemma4-12b
```

- 모델: `google/gemma-4-12B-it`
- revision: `5926caa4ec0cac5cbfadaf4077420520de1d5205`
- smoke: 1건 후 200건 c32

프로필을 바꾸기 전에는 반드시 `./stop_server.sh`로 현재 프로필 서버를 종료한다.

## 새 RunPod에서 실행

필요한 로컬 파일은 다음 두 종류뿐이다.

1. 이 번들의 최신 `.tar.gz`와 `.sha256`
2. Multimodal 원본 `open.zip` 또는 이미 풀린 `data/raw/open/`

새 Pod에서:

```bash
mkdir -p /workspace/multimodal-bias
cd /workspace/multimodal-bias
shasum -a 256 -c runpod-gemma4-repro-20260621-gemma26.tar.gz.sha256
tar -xzf runpod-gemma4-repro-20260621-gemma26.tar.gz
mkdir -p data/raw/open
unzip -q open.zip -d data/raw/open

cd runpod-gemma4-repro
chmod +x ./*.sh profiles/*.sh
export GEMMA_PROFILE=gemma4-26b-a4b-awq
export WORKSPACE_ROOT=/workspace/multimodal-bias
export DATA_ROOT=/workspace/multimodal-bias/data/raw/open
export VENV_DIR=/workspace/gemma4-vllm-cu129

./bootstrap.sh
./download_model.sh
./serve.sh
./smoke.sh
./run_full.sh
```

`bootstrap.sh`가 Python 3.12 venv를 만들고 `requirements-critical.txt`의 정확한 라이브러리를 설치한다. 환경을 손으로 따로 구성하지 않는다.

고정 run ID가 필요하면:

```bash
RUN_ID=gemma4_26b_a4b_awq_v3_full_c32_01 ./run_full.sh
```

## 시작 전 필수 확인

```bash
nvidia-smi
df -h /workspace
find "$DATA_ROOT/test/images" -type f | wc -l
curl -i http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/v1/models
```

기대값은 A6000/driver `550.127.08`, `/workspace` 여유 공간 45GiB 이상, 이미지 8,500개, health HTTP 200, 선택한 정확한 모델 ID다.

## vLLM 문제 재발 방지

- `bootstrap.sh`는 CUDA 12.9용 `vLLM 0.23.0+cu129` wheel을 직접 설치한다. 잘못된 wheel의 `libcudart.so.13` 오류를 피한다.
- venv의 `bin`을 `PATH` 앞에 둬 `ninja`를 찾게 한다.
- FastAPI/Starlette/instrumentator 호환 버전을 고정한다.
- health HTTP 200과 `/v1/models`의 정확한 ID가 모두 맞아야 smoke를 허용한다.
- 서버 로그/PID는 `runs/${PROFILE_SLUG}_vllm_server.{log,pid}`에 기록한다.

서버 종료:

```bash
./stop_server.sh
```

## 결과 검증

`run_full.sh`는 8,500개 고유 ID, 공식 순서, label 범위, parse/failure 0건, submission 8,501줄과 checksum을 검증한다. 기존 run 디렉터리가 있으면 덮어쓰지 않고 실패한다.

## 로컬에서 새 Pod로 전송

```bash
./deploy/runpod/gemma4-repro/package.sh
scp -P PORT runpod-gemma4-repro-20260621-gemma26.tar.gz* root@HOST:/workspace/multimodal-bias/
scp -P PORT open.zip root@HOST:/workspace/multimodal-bias/
```

새 대화에는 `NEXT_SESSION_PROMPT.md` 내용을 그대로 붙여넣는다.
