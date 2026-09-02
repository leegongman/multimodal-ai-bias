#!/usr/bin/env bash

PROFILE_SLUG="gemma4_26b_a4b_awq"
MODEL_ID="cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"
MODEL_REVISION="4033b16200f4152e55e100ea12dc388c537df622"
MODEL_DIR_NAME="Gemma4-26B-A4B-it-AWQ-4bit"
MODEL_ARCHITECTURES="Gemma4ForConditionalGeneration,Gemma4UnifiedForConditionalGeneration"
RUNNER_SCRIPT="run_gemma4_26b_a4b_awq_v3_vllm.py"
SMOKE_ROWS=50
VLLM_GENERATION_CONFIG="vllm"
