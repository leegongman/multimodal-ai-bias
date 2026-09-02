#!/usr/bin/env python3
"""Fail-closed validator for a completed codeshare 14006 reproduction run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-csv", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int, required=True)
    args = parser.parse_args()

    submission_path = args.run_dir / "submission.csv"
    raw_path = args.run_dir / "raw_batches.jsonl"
    summary_path = args.run_dir / "summary.json"
    for path in (submission_path, raw_path, summary_path):
        if not path.is_file():
            raise SystemExit(f"missing required artifact: {path}")

    expected = pd.read_csv(args.test_csv).head(args.expected_rows)
    submission = pd.read_csv(submission_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    raw_lines = raw_path.read_text(encoding="utf-8").splitlines()

    errors: list[str] = []
    if list(submission.columns) != ["sample_id", "label"]:
        errors.append(f"unexpected columns: {list(submission.columns)}")
    if len(submission) != args.expected_rows:
        errors.append(f"submission rows {len(submission)} != {args.expected_rows}")
    if len(raw_lines) != args.expected_rows:
        errors.append(f"raw rows {len(raw_lines)} != {args.expected_rows}")
    if submission["sample_id"].duplicated().any():
        errors.append("duplicate sample_id")
    if submission.isnull().any().any():
        errors.append("submission contains null")
    if not set(submission["label"].unique()).issubset({0, 1, 2}):
        errors.append("label outside {0,1,2}")
    if submission["sample_id"].astype(str).tolist() != expected["sample_id"].astype(str).tolist():
        errors.append("sample order or identity differs from test.csv")
    if summary.get("sample_count") != args.expected_rows:
        errors.append("summary sample_count mismatch")
    actual_hash = sha256_file(submission_path)
    if summary.get("submission_sha256") != actual_hash:
        errors.append("submission SHA-256 mismatch")

    report = {
        "valid": not errors,
        "errors": errors,
        "rows": len(submission),
        "raw_rows": len(raw_lines),
        "label_distribution": submission["label"].value_counts().sort_index().to_dict(),
        "submission_sha256": actual_hash,
        "fallback_count": sum(
            summary.get("parse_method_counts", {}).get(key, 0)
            for key in ("unknown_fallback", "zero_fallback")
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
