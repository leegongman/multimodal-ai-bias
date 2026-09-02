#!/usr/bin/env bash

PROFILE_SLUG="gemma4_12b"
MODEL_ID="google/gemma-4-12B-it"
MODEL_REVISION="5926caa4ec0cac5cbfadaf4077420520de1d5205"
MODEL_DIR_NAME="Gemma4-12B-it"
MODEL_ARCHITECTURES="Gemma4UnifiedForConditionalGeneration"
RUNNER_SCRIPT="run_gemma4_12b_v3_vllm.py"
SMOKE_ROWS=200
VLLM_GENERATION_CONFIG="auto"
