#!/usr/bin/env python3
"""Run the existing Reasoner v3 pipeline against Qwen3.5-35B-A3B AWQ."""

import run_gemma4_26b_a4b_awq_v3_vllm as runner


runner.MODEL_NAME = "cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit"


if __name__ == "__main__":
    runner.main()
