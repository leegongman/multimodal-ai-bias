#!/usr/bin/env python3

from __future__ import annotations

import importlib.metadata
import shutil
import sys

EXPECTED = {
    "vllm": "0.23.0+cu129",
    "torch": "2.11.0+cu129",
    "transformers": "5.12.1",
    "openai": "2.43.0",
    "fastapi": "0.116.1",
    "starlette": "0.47.3",
    "prometheus-fastapi-instrumentator": "7.1.0",
    "ninja": "1.13.0",
}


def main() -> None:
    errors: list[str] = []
    if sys.version_info[:2] != (3, 12):
        errors.append(f"Python must be 3.12, found {sys.version.split()[0]}")
    for package, expected in EXPECTED.items():
        actual = importlib.metadata.version(package)
        if actual != expected:
            errors.append(f"{package}: expected {expected}, found {actual}")
    if shutil.which("ninja") is None:
        errors.append("ninja is not resolvable from PATH; put the venv bin directory first")

    import torch
    import vllm

    if torch.version.cuda != "12.9":
        errors.append(f"Torch CUDA must be 12.9, found {torch.version.cuda}")
    if not torch.cuda.is_available():
        errors.append("torch.cuda.is_available() is false")
    if vllm.__version__ != EXPECTED["vllm"]:
        errors.append(f"imported vLLM version is {vllm.__version__}")
    if errors:
        raise SystemExit("ERROR:\n- " + "\n- ".join(errors))
    print("OK: exact Gemma 4 runtime versions and CUDA support verified")


if __name__ == "__main__":
    main()
