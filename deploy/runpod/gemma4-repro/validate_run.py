#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

PROFILES = {
    "gemma4-12b": {
        "model_id": "google/gemma-4-12B-it",
        "model_revision": "5926caa4ec0cac5cbfadaf4077420520de1d5205",
    },
    "gemma4-26b-a4b-awq": {
        "model_id": "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
        "model_revision": "4033b16200f4152e55e100ea12dc388c537df622",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate(
    run_dir: Path,
    expected_rows: int,
    data_root: Path | None,
    profile: str = "gemma4-12b",
) -> None:
    if profile not in PROFILES:
        raise SystemExit(f"ERROR: unsupported profile: {profile}")
    expected_profile = PROFILES[profile]
    required = [
        "run_manifest.json",
        "raw_attempts.jsonl",
        "raw_reasoner.jsonl",
        "parsed_reasoner.csv",
        "predictions.csv",
        "summary.json",
    ]
    if expected_rows == 8500:
        required.append("submission.csv")
    missing = [name for name in required if not (run_dir / name).is_file()]
    if missing:
        raise SystemExit(f"ERROR: missing run artifacts: {missing}")

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    checks = {
        "sample_count": expected_rows,
        "parse_valid_count": expected_rows,
        "parse_invalid_count": 0,
        "failure_count": 0,
        "model_name": expected_profile["model_id"],
        "model_revision": expected_profile["model_revision"],
        "concurrency": 32 if expected_rows > 1 else 1,
        "initial_max_tokens": 256,
        "retry_max_tokens": 512,
    }
    errors = [
        f"{key}: expected {expected!r}, found {summary.get(key)!r}"
        for key, expected in checks.items()
        if summary.get(key) != expected
    ]
    predictions = read_csv(run_dir / "predictions.csv")
    if len(predictions) != expected_rows:
        errors.append(f"predictions rows: expected {expected_rows}, found {len(predictions)}")
    ids = [row.get("sample_id", "") for row in predictions]
    if len(set(ids)) != len(ids) or any(not item for item in ids):
        errors.append("prediction sample IDs must be non-empty and unique")
    if any(row.get("label") not in {"0", "1", "2"} for row in predictions):
        errors.append("prediction labels must be 0, 1, or 2")

    if data_root is not None:
        official = read_csv(data_root / "sample_submission.csv")
        official_ids = [row["sample_id"] for row in official]
        if ids != official_ids:
            errors.append("prediction sample IDs/order differ from sample_submission.csv")

    if expected_rows == 8500:
        submission = run_dir / "submission.csv"
        if submission.read_bytes() != (run_dir / "predictions.csv").read_bytes():
            errors.append("submission.csv differs from predictions.csv")
        if sha256(submission) != summary.get("predictions_sha256"):
            errors.append("submission checksum differs from summary predictions checksum")
    if errors:
        raise SystemExit("ERROR:\n- " + "\n- ".join(errors))
    print(f"OK: {run_dir} contains {expected_rows} valid ordered predictions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--expected-rows", type=int, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="gemma4-12b")
    args = parser.parse_args()
    validate(args.run_dir, args.expected_rows, args.data_root, args.profile)


if __name__ == "__main__":
    main()
