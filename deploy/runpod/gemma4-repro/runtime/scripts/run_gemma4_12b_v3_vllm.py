#!/usr/bin/env python3
"""Run Gemma 4 12B Reasoner v3 through a local vLLM server."""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import hashlib
import importlib.metadata
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multimodal_bias.data_loader import load_test_records
from multimodal_bias.parsing import PARSED_REASONER_FIELDNAMES, parse_reasoner_output
from multimodal_bias.prompting.templates import build_reasoner_prompt

MODEL_NAME = "google/gemma-4-12B-it"
FULL_TEST_ROWS = 8_500
DEFAULT_INITIAL_MAX_TOKENS = 256
DEFAULT_RETRY_MAX_TOKENS = 512
MAX_EVIDENCE_CHARACTERS = 240
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
            "evidence": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_EVIDENCE_CHARACTERS,
            },
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
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sample-id")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument(
        "--initial-max-tokens", type=int, default=DEFAULT_INITIAL_MAX_TOKENS
    )
    parser.add_argument(
        "--retry-max-tokens", type=int, default=DEFAULT_RETRY_MAX_TOKENS
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.limit is not None and args.sample_id is not None:
        parser.error("--limit and --sample-id are mutually exclusive")
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")
    if args.initial_max_tokens < 1:
        parser.error("--initial-max-tokens must be positive")
    if args.retry_max_tokens <= args.initial_max_tokens:
        parser.error("--retry-max-tokens must exceed --initial-max-tokens")
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


def extract_json_object(raw_output: str) -> dict[str, Any] | None:
    """Extract the first complete JSON object, tolerating Gemma channel wrappers."""

    marker = "FINAL_ANSWER_JSON:"
    marker_index = raw_output.rfind(marker)
    candidate = (
        raw_output[marker_index + len(marker) :]
        if marker_index >= 0
        else raw_output
    )
    decoder = json.JSONDecoder()
    for index, character in enumerate(candidate):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(candidate[index:])
        except (json.JSONDecodeError, RecursionError):
            continue
        if isinstance(value, dict):
            return value
    return None


def normalize_v3_final_line(raw_output: str) -> str:
    payload = extract_json_object(raw_output)
    if payload is None:
        return raw_output
    return "FINAL_ANSWER_JSON:" + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


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


def should_retry(record: dict[str, Any]) -> bool:
    """Retry only records that do not satisfy the existing Reasoner v3 parser."""

    return parsed_row(record)["parse_status"] != "valid"


def choose_final_records(
    initial_records: list[dict[str, Any]],
    retry_records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return [retry_records.get(record["sample_id"], record) for record in initial_records]


def should_publish_submission(selected_count: int, valid_count: int) -> bool:
    return selected_count == FULL_TEST_ROWS and valid_count == FULL_TEST_ROWS


async def infer_one(
    *,
    index: int,
    sample: Any,
    client: Any,
    semaphore: asyncio.Semaphore,
    prompt_template: Path,
    max_tokens: int,
    model_revision: str,
    run_id: str,
    attempt: int,
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
            choice = response.choices[0]
            model_raw_output = choice.message.content
            if not isinstance(model_raw_output, str) or not model_raw_output.strip():
                raise ValueError("vLLM returned empty or non-text content")
            usage = response.usage
            record = {
                "run_id": run_id,
                "sample_id": sample.sample_id,
                "attempt": attempt,
                "max_tokens": max_tokens,
                "status": "generated",
                "finish_reason": choice.finish_reason,
                "prompt_version": prompt.prompt_version,
                "prompt_sha256": sha256_text(prompt_text),
                "image_path": str(sample.image_path),
                "image_sha256": sha256_bytes(image_bytes),
                "model_raw_output": model_raw_output,
                "raw_output": normalize_v3_final_line(model_raw_output),
                "elapsed_seconds": time.perf_counter() - started,
                "model_name": MODEL_NAME,
                "model_revision": model_revision,
                "input_token_count": getattr(usage, "prompt_tokens", None),
                "output_token_count": getattr(usage, "completion_tokens", None),
                "error_type": None,
                "error_message": None,
            }
        except Exception as exc:
            record = {
                "run_id": run_id,
                "sample_id": sample.sample_id,
                "attempt": attempt,
                "max_tokens": max_tokens,
                "status": "inference_failed",
                "finish_reason": None,
                "prompt_version": "reasoner_v3",
                "prompt_sha256": None,
                "image_path": str(sample.image_path),
                "image_sha256": None,
                "model_raw_output": None,
                "raw_output": None,
                "elapsed_seconds": time.perf_counter() - started,
                "model_name": MODEL_NAME,
                "model_revision": model_revision,
                "input_token_count": None,
                "output_token_count": None,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        return index, record


async def execute_batch(
    *,
    indexed_samples: list[tuple[int, Any]],
    client: Any,
    semaphore: asyncio.Semaphore,
    prompt_template: Path,
    max_tokens: int,
    model_revision: str,
    run_id: str,
    attempt: int,
) -> list[tuple[int, dict[str, Any]]]:
    tasks = [
        asyncio.create_task(
            infer_one(
                index=index,
                sample=sample,
                client=client,
                semaphore=semaphore,
                prompt_template=prompt_template,
                max_tokens=max_tokens,
                model_revision=model_revision,
                run_id=run_id,
                attempt=attempt,
            )
        )
        for index, sample in indexed_samples
    ]
    return [await future for future in asyncio.as_completed(tasks)]


async def run(args: argparse.Namespace) -> dict[str, Any]:
    from openai import AsyncOpenAI

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
        "model_revision": args.model_revision,
        "prompt_template": str(args.prompt_template.resolve()),
        "prompt_sha256": sha256_bytes(args.prompt_template.read_bytes()),
        "data_root": str(args.data_root.resolve()),
        "sample_count": len(selected),
        "limit": args.limit,
        "sample_id": args.sample_id,
        "concurrency": args.concurrency,
        "initial_max_tokens": args.initial_max_tokens,
        "retry_max_tokens": args.retry_max_tokens,
        "max_evidence_characters": MAX_EVIDENCE_CHARACTERS,
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
    started = time.perf_counter()
    initial_results = await execute_batch(
        indexed_samples=list(enumerate(selected)),
        client=client,
        semaphore=semaphore,
        prompt_template=args.prompt_template,
        max_tokens=args.initial_max_tokens,
        model_revision=args.model_revision,
        run_id=run_id,
        attempt=1,
    )
    initial_by_index = {index: record for index, record in initial_results}
    initial_records = [initial_by_index[index] for index in range(len(selected))]
    retry_indexes = [
        index for index, record in enumerate(initial_records) if should_retry(record)
    ]
    retry_results = await execute_batch(
        indexed_samples=[(index, selected[index]) for index in retry_indexes],
        client=client,
        semaphore=semaphore,
        prompt_template=args.prompt_template,
        max_tokens=args.retry_max_tokens,
        model_revision=args.model_revision,
        run_id=run_id,
        attempt=2,
    )
    await client.close()
    retry_by_sample_id = {
        record["sample_id"]: record for _, record in retry_results
    }
    ordered = choose_final_records(initial_records, retry_by_sample_id)
    elapsed = time.perf_counter() - started

    attempts_path = args.output_dir / "raw_attempts.jsonl"
    with attempts_path.open("x", encoding="utf-8") as attempts_file:
        for record in initial_records:
            attempts_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        for _, record in sorted(retry_results):
            attempts_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

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
        writer = csv.DictWriter(
            predictions_file,
            fieldnames=("sample_id", "label"),
            lineterminator="\n",
        )
        writer.writeheader()
        for row in valid_rows:
            writer.writerow({"sample_id": row["sample_id"], "label": row["parsed_label"]})

    if should_publish_submission(len(selected), len(valid_rows)):
        (args.output_dir / "submission.csv").write_bytes(predictions_path.read_bytes())

    summary = {
        **manifest,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "seconds_per_sample": elapsed / len(selected),
        "projected_8500_seconds": elapsed / len(selected) * FULL_TEST_ROWS,
        "generated_count": sum(record["status"] == "generated" for record in ordered),
        "failure_count": sum(record["status"] != "generated" for record in ordered),
        "initial_invalid_count": len(retry_indexes),
        "retry_count": len(retry_results),
        "retry_valid_count": sum(
            parsed_row(record)["parse_status"] == "valid"
            for _, record in retry_results
        ),
        "parse_valid_count": len(valid_rows),
        "parse_invalid_count": len(selected) - len(valid_rows),
        "gpu_after": gpu_snapshot(),
        "raw_attempts_sha256": sha256_bytes(attempts_path.read_bytes()),
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
