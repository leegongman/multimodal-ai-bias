#!/usr/bin/env python3
"""Smoke-test candidate reasoner prompts against the 14006 Qwen3.5 vLLM path.

The model/server/generation/image settings match the public-strong 14006
reproduction path. The only intended variable is the candidate reasoner prompt
loaded from candidate_prompts.md.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import hashlib
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI


MODEL_NAME = "Qwen/Qwen3.5-9B"
MODEL_REVISION = "c202236235762e1c871ad0ccb60c8ee5ba337b9a"
MAX_NEW_TOKENS = 256
MAX_PIXELS = 200704
MIN_PIXELS = 50176

_CANDIDATE_RE = re.compile(
    r"## Candidate (?P<key>[A-G]): (?P<title>[^\n]+)\n.*?```text\n(?P<prompt>.*?)\n```",
    re.DOTALL,
)
_COMMON_RE = re.compile(r"## Common User Template\n\n.*?```text\n(?P<template>.*?)\n```", re.DOTALL)
_FINAL_JSON_RE = re.compile(r"FINAL_ANSWER_JSON\s*:\s*(\{.*\})\s*$", re.DOTALL)
_UNK_PAT = re.compile(
    r"not enough|cannot|can.?t be|can.?t answer|undetermined|undeterminable|"
    r"not known|unknown|not answerable|no answer|not determinable|can.?t tell|"
    r"not sure|not be determined|not enough info",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-prompts", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--candidates", default="A,B,C,D,E,F,G")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")
    if args.output_dir.exists():
        parser.error(f"output directory already exists: {args.output_dir}")
    return args


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def data_url(image_bytes: bytes, suffix: str) -> str:
    media_type = "image/png" if suffix.lower() == ".png" else "image/jpeg"
    return f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"


def parse_options(answers_field: Any) -> list[str]:
    return answers_field if isinstance(answers_field, list) else json.loads(answers_field)


def find_unknown_index(options: list[str]) -> int:
    hits = [i for i, option in enumerate(options) if _UNK_PAT.search(option)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return min(hits, key=lambda index: len(options[index]))
    return -1


def format_answers(options: list[str]) -> str:
    return "\n".join(f"{index}. {option}" for index, option in enumerate(options))


def load_candidate_prompts(path: Path) -> tuple[str, dict[str, dict[str, str]]]:
    text = path.read_text(encoding="utf-8")
    common_match = _COMMON_RE.search(text)
    if not common_match:
        raise ValueError("Could not parse Common User Template from candidate prompts.")
    candidates: dict[str, dict[str, str]] = {}
    for match in _CANDIDATE_RE.finditer(text):
        candidates[match.group("key")] = {
            "key": match.group("key"),
            "title": match.group("title").strip(),
            "system_prompt": match.group("prompt").strip(),
        }
    missing = [key for key in "ABCDEFG" if key not in candidates]
    if missing:
        raise ValueError(f"Missing candidate prompts: {missing}")
    return common_match.group("template").strip(), candidates


def build_user_text(template: str, row: dict[str, Any], options: list[str]) -> str:
    replacements = {
        "{sample_id}": str(row["sample_id"]),
        "{context}": str(row["context"]),
        "{question}": str(row["question"]),
        "{answers}": format_answers(options),
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def parse_final_json(text: str, options: list[str]) -> tuple[int | None, str, dict[str, Any] | None, str | None]:
    if not text:
        return None, "empty", None, "empty response"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    final_line = lines[-1] if lines else text.strip()
    match = _FINAL_JSON_RE.search(final_line)
    if not match:
        # fallback for diagnostics only
        digit_matches = re.findall(r"\b([012])\b", text)
        if digit_matches:
            return int(digit_matches[-1]), "digit_fallback", None, "missing FINAL_ANSWER_JSON"
        return None, "parse_failed", None, "missing FINAL_ANSWER_JSON"
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return None, "json_decode_error", None, str(exc)
    label = payload.get("label")
    if isinstance(label, int):
        label = str(label)
    if label not in {"0", "1", "2"}:
        return None, "invalid_label", payload, f"invalid label: {label!r}"
    label_int = int(label)
    expected_unknown = find_unknown_index(options)
    uncertainty_option_index = payload.get("uncertainty_option_index")
    uncertainty_signal = payload.get("uncertainty_signal")
    contract_errors: list[str] = []
    if uncertainty_option_index != expected_unknown:
        contract_errors.append(
            f"uncertainty_option_index {uncertainty_option_index!r} != expected {expected_unknown}"
        )
    if uncertainty_signal is not None and bool(uncertainty_signal) != (label_int == expected_unknown):
        contract_errors.append("uncertainty_signal mismatch")
    method = "final_json" if not contract_errors else "final_json_contract_warning"
    return label_int, method, payload, "; ".join(contract_errors) or None


async def infer_one(
    index: int,
    row: dict[str, Any],
    image_dir: Path,
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    system_prompt: str,
    user_template: str,
) -> tuple[int, dict[str, Any]]:
    async with semaphore:
        started = time.perf_counter()
        options = parse_options(row["answers"])
        image_path = image_dir / os.path.basename(row["image_path"])
        image_bytes = image_path.read_bytes()
        user_text = build_user_text(user_template, row, options)
        try:
            response = await client.chat.completions.create(
                model=client.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url(image_bytes, image_path.suffix)},
                            },
                            {"type": "text", "text": user_text},
                        ],
                    },
                ],
                max_tokens=MAX_NEW_TOKENS,
                temperature=0.0,
                extra_body={
                    "top_k": 1,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            raw_output = response.choices[0].message.content
            if not isinstance(raw_output, str):
                raise ValueError("non-string vLLM response")
            label, parse_method, parsed_json, parse_error = parse_final_json(raw_output, options)
            usage = response.usage
            status = "generated" if label is not None else "parse_failed"
            record = {
                "sample_id": row["sample_id"],
                "status": status,
                "label": label,
                "answer_text": options[label] if label is not None else None,
                "unknown_index": find_unknown_index(options),
                "parse_method": parse_method,
                "parse_error": parse_error,
                "parsed_json": parsed_json,
                "raw_output": raw_output,
                "image_sha256": sha256_bytes(image_bytes),
                "elapsed_seconds": time.perf_counter() - started,
                "input_token_count": getattr(usage, "prompt_tokens", None),
                "output_token_count": getattr(usage, "completion_tokens", None),
                "error": None,
            }
        except Exception as exc:
            record = {
                "sample_id": row["sample_id"],
                "status": "failed",
                "label": None,
                "answer_text": None,
                "unknown_index": find_unknown_index(options),
                "parse_method": None,
                "parse_error": None,
                "parsed_json": None,
                "raw_output": None,
                "image_sha256": sha256_bytes(image_bytes),
                "elapsed_seconds": time.perf_counter() - started,
                "input_token_count": None,
                "output_token_count": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        return index, record


async def run_candidate(
    args: argparse.Namespace,
    candidate: dict[str, str],
    user_template: str,
    rows: list[dict[str, Any]],
    image_dir: Path,
) -> dict[str, Any]:
    candidate_dir = args.output_dir / f"candidate_{candidate['key']}"
    candidate_dir.mkdir(parents=True)
    client = AsyncOpenAI(base_url=args.base_url, api_key="EMPTY", timeout=300.0)
    client.model_name = args.model_name  # type: ignore[attr-defined]
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [
        asyncio.create_task(
            infer_one(
                index=index,
                row=row,
                image_dir=image_dir,
                client=client,
                semaphore=semaphore,
                system_prompt=candidate["system_prompt"],
                user_template=user_template,
            )
        )
        for index, row in enumerate(rows)
    ]
    completed: list[dict[str, Any] | None] = [None] * len(tasks)
    started = time.perf_counter()
    partial_path = candidate_dir / "raw.partial.jsonl"
    with partial_path.open("x", encoding="utf-8") as partial:
        for future in asyncio.as_completed(tasks):
            index, record = await future
            completed[index] = record
            partial.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            partial.flush()
    await client.close()
    elapsed = time.perf_counter() - started
    ordered = [record for record in completed if record is not None]
    raw_path = candidate_dir / "raw.jsonl"
    with raw_path.open("x", encoding="utf-8") as raw:
        for record in ordered:
            raw.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    labels = [record["label"] for record in ordered if record["label"] is not None]
    methods = [record["parse_method"] for record in ordered if record["parse_method"]]
    statuses = [record["status"] for record in ordered]
    summary = {
        "candidate_key": candidate["key"],
        "candidate_title": candidate["title"],
        "model_name": args.model_name,
        "model_revision": args.model_revision,
        "sample_count": len(rows),
        "concurrency": args.concurrency,
        "elapsed_seconds": elapsed,
        "seconds_per_sample": elapsed / len(rows),
        "status_counts": dict(sorted(Counter(statuses).items())),
        "label_distribution": dict(sorted(Counter(labels).items())),
        "parse_method_counts": dict(sorted(Counter(methods).items())),
        "failure_count": sum(1 for status in statuses if status == "failed"),
        "parse_failed_count": sum(1 for status in statuses if status == "parse_failed"),
        "contract_warning_count": sum(
            1 for record in ordered if record["parse_method"] == "final_json_contract_warning"
        ),
        "system_prompt_sha256": sha256_bytes(candidate["system_prompt"].encode()),
        "raw_sha256": sha256_bytes(raw_path.read_bytes()),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    (candidate_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


async def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True)
    user_template, candidates = load_candidate_prompts(args.candidate_prompts)
    selected = [key.strip() for key in args.candidates.split(",") if key.strip()]
    with (args.data_dir / "test.csv").open(encoding="utf-8", newline="") as test_file:
        rows = list(csv.DictReader(test_file))[: args.limit]
    image_dir = args.data_dir / "images"
    missing = [row["sample_id"] for row in rows if not (image_dir / os.path.basename(row["image_path"])).is_file()]
    if missing:
        raise FileNotFoundError(f"missing image for {missing[0]}")

    all_summaries = []
    for key in selected:
        summary = await run_candidate(args, candidates[key], user_template, rows, image_dir)
        all_summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    (args.output_dir / "summary.json").write_text(
        json.dumps(
            {
                "model_name": args.model_name,
                "model_revision": args.model_revision,
                "data_dir": str(args.data_dir),
                "candidate_prompts": str(args.candidate_prompts),
                "limit": args.limit,
                "concurrency": args.concurrency,
                "summaries": all_summaries,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()
