#!/usr/bin/env python3
"""Run Qwen3.5-9B Reasoner v3 through a local vLLM server."""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import hashlib
import importlib.metadata
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from multimodal_bias.data_loader import load_test_records
from multimodal_bias.parsing import PARSED_REASONER_FIELDNAMES, parse_reasoner_output
from multimodal_bias.prompting.templates import build_reasoner_prompt

MODEL_NAME = "Qwen/Qwen3.5-9B"
MODEL_REVISION = "c202236235762e1c871ad0ccb60c8ee5ba337b9a"
FULL_TEST_ROWS = 8_500
DECISIVE_EVIDENCE_TYPES = [
    "stated_text_fact",
    "objective_visible_evidence",
    "elimination",
]
REASONER_V3_REQUIRED_FIELDS = [
    "label",
    "uncertainty_option_index",
    "evidence",
    "evidence_type",
    "uncertainty_signal",
    "protected_attribute_risk",
    "schema_version",
]


def semantic_variant_schema(label_index: int, uncertainty_index: int) -> dict[str, Any]:
    selected_uncertainty = label_index == uncertainty_index
    return {
        "type": "object",
        "properties": {
            "label": {"const": str(label_index)},
            "uncertainty_option_index": {"const": uncertainty_index},
            "evidence": {"type": "string", "minLength": 1},
            "evidence_type": (
                {"const": "insufficient_evidence"}
                if selected_uncertainty
                else {"enum": DECISIVE_EVIDENCE_TYPES}
            ),
            "uncertainty_signal": {"const": selected_uncertainty},
            "protected_attribute_risk": {"type": "boolean"},
            "schema_version": {"const": "reasoner_output_v3"},
        },
        "required": REASONER_V3_REQUIRED_FIELDS,
        "additionalProperties": False,
    }


REASONER_V3_SEMANTIC_VARIANTS = [
    semantic_variant_schema(label_index, uncertainty_index)
    for label_index in range(3)
    for uncertainty_index in range(3)
]
REASONER_V3_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "reasoner_output_v3",
        "strict": True,
        "schema": {"anyOf": REASONER_V3_SEMANTIC_VARIANTS},
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--prompt-template", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sample-id")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.limit is not None and args.sample_id is not None:
        parser.error("--limit and --sample-id are mutually exclusive")
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")
    if args.max_tokens < 1:
        parser.error("--max-tokens must be positive")
    return args


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def gpu_snapshot() -> str:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or result.stderr.strip()


def data_url(image_bytes: bytes, suffix: str) -> str:
    media_type = "image/png" if suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def normalize_v3_final_line(raw_output: str) -> str:
    """Canonicalize a valid multiline final JSON object without changing its content."""

    marker = "FINAL_ANSWER_JSON:"
    marker_index = raw_output.rfind(marker)
    payload_text = (
        raw_output[marker_index + len(marker) :].strip()
        if marker_index >= 0
        else raw_output.strip()
    )
    try:
        payload = json.loads(payload_text)
    except (json.JSONDecodeError, RecursionError):
        return raw_output
    canonical_final = marker + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    prefix = raw_output[:marker_index].rstrip() if marker_index >= 0 else ""
    return f"{prefix}\n\n{canonical_final}" if prefix else canonical_final


async def infer_one(
    *,
    index: int,
    sample: Any,
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    prompt_template: Path,
    max_tokens: int,
    run_id: str,
) -> tuple[int, dict[str, Any]]:
    async with semaphore:
        started = time.perf_counter()
        try:
            image_bytes = sample.image_path.read_bytes()
            prompt = build_reasoner_prompt(sample, prompt_template)
            prompt_text = f"{prompt.system_prompt}\n\n{prompt.user_prompt}"
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": prompt.system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url(image_bytes, sample.image_path.suffix)
                                },
                            },
                            {"type": "text", "text": prompt.user_prompt},
                        ],
                    },
                ],
                max_tokens=max_tokens,
                temperature=0.0,
                response_format=REASONER_V3_RESPONSE_FORMAT,
                extra_body={
                    "top_k": 1,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            model_raw_output = response.choices[0].message.content
            if not isinstance(model_raw_output, str) or not model_raw_output.strip():
                raise ValueError("vLLM returned empty or non-text content")
            raw_output = normalize_v3_final_line(model_raw_output)
            usage = response.usage
            record = {
                "run_id": run_id,
                "sample_id": sample.sample_id,
                "status": "generated",
                "prompt_version": prompt.prompt_version,
                "prompt_sha256": sha256_text(prompt_text),
                "image_path": str(sample.image_path),
                "image_sha256": sha256_bytes(image_bytes),
                "model_raw_output": model_raw_output,
                "raw_output": raw_output,
                "elapsed_seconds": time.perf_counter() - started,
                "model_name": MODEL_NAME,
                "model_revision": MODEL_REVISION,
                "input_token_count": getattr(usage, "prompt_tokens", None),
                "output_token_count": getattr(usage, "completion_tokens", None),
                "error_type": None,
                "error_message": None,
            }
        except Exception as exc:
            record = {
                "run_id": run_id,
                "sample_id": sample.sample_id,
                "status": "inference_failed",
                "prompt_version": "reasoner_v3",
                "prompt_sha256": None,
                "image_path": str(sample.image_path),
                "image_sha256": None,
                "model_raw_output": None,
                "raw_output": None,
                "elapsed_seconds": time.perf_counter() - started,
                "model_name": MODEL_NAME,
                "model_revision": MODEL_REVISION,
                "input_token_count": None,
                "output_token_count": None,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        return index, record


def parsed_row(record: dict[str, Any]) -> dict[str, str]:
    if record["status"] == "generated":
        parsed = parse_reasoner_output(
            record["raw_output"],
            run_id=record["run_id"],
            sample_id=record["sample_id"],
            schema_mode="v3",
        )
    else:
        return {
            "run_id": record["run_id"],
            "sample_id": record["sample_id"],
            "parsed_label": "",
            "uncertainty_option_index": "",
            "evidence_summary": "",
            "evidence_type": "",
            "uncertainty_signal": "",
            "risk_flags": '["invalid_parse"]',
            "schema_version": "",
            "parse_status": "source_failed",
            "parse_error": record["error_message"] or "inference failed",
        }
    return {
        "run_id": parsed.run_id,
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


async def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.output_dir.exists():
        raise FileExistsError(f"output directory already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    run_id = args.output_dir.name
    records = load_test_records(args.data_root, allow_missing_images=True)
    if args.sample_id is not None:
        selected = tuple(record for record in records if record.sample_id == args.sample_id)
        if not selected:
            raise ValueError(f"sample ID not found in official test data: {args.sample_id}")
    else:
        selected = records[: args.limit] if args.limit is not None else records
    missing = [str(record.image_path) for record in selected if not record.image_path.is_file()]
    if missing:
        raise FileNotFoundError(f"selected input images are missing; first={missing[0]}")

    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "prompt_template": str(args.prompt_template.resolve()),
        "prompt_sha256": sha256_bytes(args.prompt_template.read_bytes()),
        "data_root": str(args.data_root.resolve()),
        "sample_count": len(selected),
        "limit": args.limit,
        "sample_id": args.sample_id,
        "concurrency": args.concurrency,
        "max_tokens": args.max_tokens,
        "enable_thinking": False,
        "temperature": 0.0,
        "top_k": 1,
        "vllm_version": importlib.metadata.version("vllm"),
        "openai_version": importlib.metadata.version("openai"),
        "gpu_before": gpu_snapshot(),
    }
    (args.output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    client = AsyncOpenAI(base_url=args.base_url, api_key="EMPTY", timeout=300.0)
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [
        asyncio.create_task(
            infer_one(
                index=index,
                sample=sample,
                client=client,
                semaphore=semaphore,
                prompt_template=args.prompt_template,
                max_tokens=args.max_tokens,
                run_id=run_id,
            )
        )
        for index, sample in enumerate(selected)
    ]
    completed: list[dict[str, Any] | None] = [None] * len(tasks)
    started = time.perf_counter()
    partial_path = args.output_dir / "raw_reasoner.partial.jsonl"
    with partial_path.open("x", encoding="utf-8") as partial_file:
        for future in asyncio.as_completed(tasks):
            index, record = await future
            completed[index] = record
            partial_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            partial_file.flush()
            if index == 0 or (index + 1) % 25 == 0:
                os.fsync(partial_file.fileno())
        os.fsync(partial_file.fileno())
    await client.close()
    elapsed = time.perf_counter() - started
    ordered = [record for record in completed if record is not None]
    raw_path = args.output_dir / "raw_reasoner.jsonl"
    with raw_path.open("x", encoding="utf-8") as raw_file:
        for record in ordered:
            raw_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    parsed_rows = [parsed_row(record) for record in ordered]
    parsed_path = args.output_dir / "parsed_reasoner.csv"
    with parsed_path.open("x", encoding="utf-8", newline="") as parsed_file:
        writer = csv.DictWriter(parsed_file, fieldnames=PARSED_REASONER_FIELDNAMES)
        writer.writeheader()
        writer.writerows(parsed_rows)

    valid_rows = [row for row in parsed_rows if row["parse_status"] == "valid"]
    predictions_path = args.output_dir / "predictions.csv"
    with predictions_path.open("x", encoding="utf-8", newline="") as predictions_file:
        writer = csv.DictWriter(predictions_file, fieldnames=("sample_id", "label"))
        writer.writeheader()
        for row in valid_rows:
            writer.writerow({"sample_id": row["sample_id"], "label": row["parsed_label"]})

    if len(selected) == FULL_TEST_ROWS and len(valid_rows) == FULL_TEST_ROWS:
        (args.output_dir / "submission.csv").write_bytes(predictions_path.read_bytes())

    summary = {
        **manifest,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "seconds_per_sample": elapsed / len(selected),
        "projected_8500_seconds": elapsed / len(selected) * FULL_TEST_ROWS,
        "generated_count": sum(record["status"] == "generated" for record in ordered),
        "failure_count": sum(record["status"] != "generated" for record in ordered),
        "parse_valid_count": len(valid_rows),
        "parse_invalid_count": len(selected) - len(valid_rows),
        "gpu_after": gpu_snapshot(),
        "raw_reasoner_sha256": sha256_bytes(raw_path.read_bytes()),
        "parsed_reasoner_sha256": sha256_bytes(parsed_path.read_bytes()),
        "predictions_sha256": sha256_bytes(predictions_path.read_bytes()),
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    summary = asyncio.run(run(parse_args()))
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if summary["failure_count"] or summary["parse_invalid_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
