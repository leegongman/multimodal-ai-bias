#!/usr/bin/env python3
"""Run the proven Reasoner v3 pipeline with Gemma 4 26B-A4B AWQ."""

import run_gemma4_12b_v3_vllm as runner


runner.MODEL_NAME = "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"


if __name__ == "__main__":
    runner.main()
