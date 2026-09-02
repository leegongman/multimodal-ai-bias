#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

FORBIDDEN_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".zip", ".tar", ".gz"}
FORBIDDEN_PARTS = {".venv", "venv", "models", "data", "runs", "__pycache__"}
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----"),
    re.compile(rb"hf_[A-Za-z0-9]{24,}"),
]


def validate(root: Path) -> None:
    errors: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            errors.append(f"forbidden directory payload: {relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden binary/archive payload: {relative}")
        if path.stat().st_size > 5_000_000:
            errors.append(f"unexpected file over 5 MB: {relative}")
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            errors.append(f"secret-like content detected: {relative}")
    checksum_path = root / "SHA256SUMS"
    if checksum_path.is_file():
        for line in checksum_path.read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            target = root / name.lstrip("* ")
            if not target.is_file():
                errors.append(f"checksum target missing: {name}")
            elif hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                errors.append(f"checksum mismatch: {name}")

    prompt_path = root / "runtime" / "configs" / "prompts" / "reasoner_v3.yaml"
    if prompt_path.is_file():
        prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        for provenance_path in sorted(
            (root / "provenance").glob("known-good-runtime*.json")
        ):
            relative = provenance_path.relative_to(root)
            try:
                provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
                expected_prompt_sha256 = provenance["full_run"]["prompt_sha256"]
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                errors.append(f"invalid prompt provenance: {relative}: {error}")
                continue
            if prompt_sha256 != expected_prompt_sha256:
                errors.append(f"prompt provenance mismatch: {relative}")
    if errors:
        raise SystemExit("ERROR:\n- " + "\n- ".join(errors))
    print("OK: bundle contains no credentials, weights, datasets, environments, runs, or archives")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    validate(args.root.resolve())


if __name__ == "__main__":
    main()
