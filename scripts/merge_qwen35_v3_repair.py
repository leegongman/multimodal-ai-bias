#!/usr/bin/env python3
"""Merge one valid targeted retry into an immutable Qwen3.5 v3 full run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multimodal_bias.data_loader import load_test_records
from multimodal_bias.parsing import PARSED_REASONER_FIELDNAMES, parse_reasoner_output

FULL_TEST_ROWS = 8_500


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--source-run-dir", type=Path, required=True)
    parser.add_argument("--repair-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-id", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def parsed_row(record: dict[str, Any], run_id: str) -> dict[str, str]:
    parsed = parse_reasoner_output(
        record["raw_output"],
        run_id=run_id,
        sample_id=record["sample_id"],
        schema_mode="v3",
    )
    return {
        "run_id": run_id,
        "sample_id": parsed.sample_id,
        "parsed_label": parsed.parsed_label or "",
        "uncertainty_option_index": (
            "" if parsed.uncertainty_option_index is None else str(parsed.uncertainty_option_index)
        ),
        "evidence_summary": parsed.evidence_summary or "",
        "evidence_type": parsed.evidence_type or "",
        "uncertainty_signal": (
            "" if parsed.uncertainty_signal is None else str(parsed.uncertainty_signal).lower()
        ),
        "risk_flags": json.dumps(list(parsed.risk_flags), separators=(",", ":")),
        "schema_version": parsed.schema_version or "",
        "parse_status": parsed.parse_status,
        "parse_error": parsed.parse_error or "",
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    args = parse_args()
    require(not args.output_dir.exists(), f"output directory already exists: {args.output_dir}")

    official_ids = tuple(record.sample_id for record in load_test_records(args.data_root))
    require(len(official_ids) == FULL_TEST_ROWS, "official test data must contain 8,500 rows")

    source_raw_path = args.source_run_dir / "raw_reasoner.jsonl"
    source_parsed_path = args.source_run_dir / "parsed_reasoner.csv"
    repair_raw_path = args.repair_run_dir / "raw_reasoner.jsonl"
    repair_parsed_path = args.repair_run_dir / "parsed_reasoner.csv"
    input_paths = (source_raw_path, source_parsed_path, repair_raw_path, repair_parsed_path)
    input_hashes_before = {str(path.resolve()): sha256_file(path) for path in input_paths}

    source_raw = read_jsonl(source_raw_path)
    source_parsed = read_csv(source_parsed_path)
    repair_raw = read_jsonl(repair_raw_path)
    repair_parsed = read_csv(repair_parsed_path)

    require(len(source_raw) == FULL_TEST_ROWS, "source raw run must contain 8,500 rows")
    require(len(source_parsed) == FULL_TEST_ROWS, "source parsed run must contain 8,500 rows")
    require(
        tuple(row["sample_id"] for row in source_raw) == official_ids,
        "source raw order mismatch",
    )
    require(
        tuple(row["sample_id"] for row in source_parsed) == official_ids,
        "source parsed order mismatch",
    )
    invalid_ids = [row["sample_id"] for row in source_parsed if row["parse_status"] != "valid"]
    require(
        invalid_ids == [args.sample_id],
        f"expected only {args.sample_id} invalid; got {invalid_ids}",
    )
    require(
        len(repair_raw) == 1 and repair_raw[0]["sample_id"] == args.sample_id,
        "repair raw mismatch",
    )
    require(
        len(repair_parsed) == 1
        and repair_parsed[0]["sample_id"] == args.sample_id
        and repair_parsed[0]["parse_status"] == "valid",
        "repair run must contain one valid parsed row",
    )

    output_run_id = args.output_dir.name
    replacement = dict(repair_raw[0])
    merged_raw: list[dict[str, Any]] = []
    for source_record in source_raw:
        record = (
            replacement
            if source_record["sample_id"] == args.sample_id
            else dict(source_record)
        )
        record = dict(record)
        record["run_id"] = output_run_id
        record["origin_run_id"] = (
            args.repair_run_dir.name
            if record["sample_id"] == args.sample_id
            else args.source_run_dir.name
        )
        merged_raw.append(record)

    parsed_rows = [parsed_row(record, output_run_id) for record in merged_raw]
    invalid_after = [row["sample_id"] for row in parsed_rows if row["parse_status"] != "valid"]
    require(not invalid_after, f"merged run still contains invalid rows: {invalid_after}")

    args.output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output_run_id}.", dir=args.output_dir.parent
    ) as temp_name:
        temp_dir = Path(temp_name)
        raw_path = temp_dir / "raw_reasoner.jsonl"
        with raw_path.open("x", encoding="utf-8") as file:
            for record in merged_raw:
                file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

        parsed_path = temp_dir / "parsed_reasoner.csv"
        with parsed_path.open("x", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=PARSED_REASONER_FIELDNAMES)
            writer.writeheader()
            writer.writerows(parsed_rows)

        predictions_path = temp_dir / "predictions.csv"
        with predictions_path.open("x", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=("sample_id", "label"), lineterminator="\n")
            writer.writeheader()
            writer.writerows(
                {"sample_id": row["sample_id"], "label": row["parsed_label"]}
                for row in parsed_rows
            )
        submission_path = temp_dir / "submission.csv"
        submission_path.write_bytes(predictions_path.read_bytes())

        manifest = {
            "run_id": output_run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_run_id": args.source_run_dir.name,
            "repair_run_id": args.repair_run_dir.name,
            "repaired_sample_id": args.sample_id,
            "sample_count": FULL_TEST_ROWS,
            "input_sha256": input_hashes_before,
        }
        (temp_dir / "run_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary = {
            **manifest,
            "parse_valid_count": FULL_TEST_ROWS,
            "parse_invalid_count": 0,
            "raw_reasoner_sha256": sha256_file(raw_path),
            "parsed_reasoner_sha256": sha256_file(parsed_path),
            "predictions_sha256": sha256_file(predictions_path),
            "submission_sha256": sha256_file(submission_path),
        }
        (temp_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        input_hashes_after = {str(path.resolve()): sha256_file(path) for path in input_paths}
        require(input_hashes_after == input_hashes_before, "an input artifact changed during merge")
        os.rename(temp_dir, args.output_dir)

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
