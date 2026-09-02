#!/usr/bin/env python3
"""Run the existing Reasoner v3 pipeline against Pixtral-12B."""

import run_gemma4_26b_a4b_awq_v3_vllm as runner


runner.MODEL_NAME = "mistralai/Pixtral-12B-2409"
runner.EXTRA_BODY = {"top_k": 1}


if __name__ == "__main__":
    runner.main()
