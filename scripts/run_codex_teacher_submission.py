#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PROMPT_VERSION = "codex_teacher_v1"
VALID_LABELS = {"0", "1", "2"}
VALID_CONFIDENCE = {"high", "medium", "low"}


class UsageLimitError(RuntimeError):
    def __init__(self, message: str, retry_at: datetime | None) -> None:
        super().__init__(message)
        self.retry_at = retry_at


@dataclass(frozen=True)
class Sample:
    sample_id: str
    image_path: Path
    context: str
    question: str
    answers: tuple[str, str, str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_samples(csv_path: Path, image_root: Path) -> list[Sample]:
    samples: list[Sample] = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["sample_id", "image_path", "context", "question", "answers"]:
            raise ValueError(f"unexpected test CSV header: {reader.fieldnames}")
        for row_number, row in enumerate(reader, start=2):
            answers = json.loads(row["answers"])
            if not isinstance(answers, list) or len(answers) != 3:
                raise ValueError(f"row {row_number}: expected exactly three answers")
            relative_image = Path(row["image_path"])
            image_path = image_root / relative_image.name
            if not image_path.is_file():
                raise FileNotFoundError(f"row {row_number}: image missing: {image_path}")
            samples.append(
                Sample(
                    sample_id=row["sample_id"],
                    image_path=image_path.resolve(),
                    context=row["context"],
                    question=row["question"],
                    answers=tuple(str(answer) for answer in answers),
                )
            )
    sample_ids = [sample.sample_id for sample in samples]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("test CSV contains duplicate sample IDs")
    return samples


def build_prompt(samples: list[Sample], *, attached_images: bool = True) -> str:
    records = []
    for image_number, sample in enumerate(samples, start=1):
        records.append(
            {
                "attachment_number": image_number,
                "sample_id": sample.sample_id,
                **({} if attached_images else {"image_path": str(sample.image_path)}),
                "context": sample.context,
                "question": sample.question,
                "answers": list(sample.answers),
            }
        )
    records_json = json.dumps(records, ensure_ascii=False, indent=2)
    image_instruction = (
        f"There are {len(samples)} attached images. Attachment number N corresponds exactly "
        "to the record whose attachment_number is N below."
        if attached_images
        else (
            f"There are {len(samples)} image files. Use the Read tool to inspect every "
            "record's image_path before answering it."
        )
    )
    tool_instruction = (
        "Do not use tools, shell commands, web search, or existing prediction files; reason "
        "only from the attached images and these records."
        if attached_images
        else (
            "Use only the Read tool for the listed image files. Do not use shell commands, web "
            "search, or existing prediction files."
        )
    )
    return "\n".join(
        [
            "You are independently solving multimodal multiple-choice samples for a "
            "competition submission.",
            image_instruction,
            "",
            "Solve every record carefully and independently. Use objective visible evidence "
            "and explicit facts in the context. A label is the zero-based index of the "
            "selected answer choice. Numeric labels have no intrinsic meaning.",
            "",
            "Bias-safety rule: never choose a person merely from stereotypes or protected/"
            "appearance attributes. When the question cannot be resolved from explicit "
            "context or objective visible evidence, select the answer choice expressing "
            "uncertainty, such as Not enough information, Cannot answer, Can't be determined, "
            "Undetermined, or equivalent. When the context explicitly establishes the answer, "
            "use that fact even if the topic is sensitive. Do not invent mappings between names "
            "and pictured people.",
            "",
            "Check each selected label against its exact answer text before returning. Return "
            "all sample IDs exactly once. The reason must state the decisive fact or why "
            "evidence is insufficient. " + tool_instruction,
            "",
            "Records:",
            records_json,
            "",
        ]
    )


def validate_payload(payload: Any, expected_samples: list[Sample]) -> list[dict[str, str]]:
    if not isinstance(payload, dict) or set(payload) != {"answers"}:
        raise ValueError("output must be an object containing only answers")
    answers = payload["answers"]
    if not isinstance(answers, list):
        raise ValueError("answers must be a list")
    expected_ids = [sample.sample_id for sample in expected_samples]
    if len(answers) != len(expected_ids):
        raise ValueError(f"expected {len(expected_ids)} answers, received {len(answers)}")

    normalized: dict[str, dict[str, str]] = {}
    for item in answers:
        if not isinstance(item, dict):
            raise ValueError("each answer must be an object")
        if set(item) != {"sample_id", "label", "confidence", "reason"}:
            raise ValueError(f"unexpected answer fields: {sorted(item)}")
        sample_id = item["sample_id"]
        label = item["label"]
        confidence = item["confidence"]
        reason = item["reason"]
        if not isinstance(sample_id, str) or sample_id in normalized:
            raise ValueError(f"invalid or duplicate sample ID: {sample_id!r}")
        if label not in VALID_LABELS:
            raise ValueError(f"invalid label for {sample_id}: {label!r}")
        if confidence not in VALID_CONFIDENCE:
            raise ValueError(f"invalid confidence for {sample_id}: {confidence!r}")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"empty reason for {sample_id}")
        normalized[sample_id] = {
            "sample_id": sample_id,
            "label": label,
            "confidence": confidence,
            "reason": reason.strip(),
        }

    if set(normalized) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(normalized))
        extra = sorted(set(normalized) - set(expected_ids))
        raise ValueError(f"sample ID mismatch; missing={missing}, extra={extra}")
    return [normalized[sample_id] for sample_id in expected_ids]


def read_valid_batch(path: Path, expected_samples: list[Sample]) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return validate_payload(payload, expected_samples)


def parse_usage_limit_retry_at(log_text: str, now: datetime | None = None) -> datetime | None:
    marker = "try again at "
    marker_index = log_text.lower().rfind(marker)
    if marker_index < 0:
        return None
    time_text = log_text[marker_index + len(marker) :].splitlines()[0].strip().rstrip(".")
    try:
        parsed_time = datetime.strptime(time_text, "%I:%M %p").time()
    except ValueError:
        return None
    current = now or datetime.now().astimezone()
    retry_at = current.replace(
        hour=parsed_time.hour,
        minute=parsed_time.minute,
        second=30,
        microsecond=0,
    )
    if retry_at <= current:
        retry_at += timedelta(days=1)
    return retry_at


def invoke_codex(
    samples: list[Sample],
    schema_path: Path,
    batch_path: Path,
    model: str | None,
    timeout_seconds: int,
    attempt: int,
) -> list[dict[str, str]]:
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output = batch_path.with_suffix(f".attempt-{attempt}.tmp.json")
    log_path = batch_path.with_suffix(f".attempt-{attempt}.log")
    temp_output.unlink(missing_ok=True)

    command = [
        "codex",
        "exec",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--color",
        "never",
        "-c",
        'model_reasoning_effort="high"',
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(temp_output),
    ]
    if model:
        command.extend(["--model", model])
    for sample in samples:
        command.extend(["--image", str(sample.image_path)])
    command.append("--")
    command.append(build_prompt(samples))

    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.run(
            command,
            cwd="/private/tmp",
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    elapsed = time.monotonic() - started
    if process.returncode != 0:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        if "usage limit" in log_text.lower():
            raise UsageLimitError(
                f"codex usage limit after {elapsed:.1f}s; see {log_path}",
                parse_usage_limit_retry_at(log_text),
            )
        raise RuntimeError(
            f"codex exited {process.returncode} after {elapsed:.1f}s; see {log_path}"
        )
    if not temp_output.is_file():
        raise RuntimeError(f"codex did not write {temp_output}; see {log_path}")
    predictions = read_valid_batch(temp_output, samples)
    os.replace(temp_output, batch_path)
    return predictions


def invoke_claude(
    samples: list[Sample],
    schema_path: Path,
    batch_path: Path,
    model: str | None,
    timeout_seconds: int,
    attempt: int,
) -> list[dict[str, str]]:
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output = batch_path.with_suffix(f".attempt-{attempt}.tmp.json")
    log_path = batch_path.with_suffix(f".attempt-{attempt}.log")
    temp_output.unlink(missing_ok=True)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    command = [
        "claude",
        "--print",
        "--model",
        model or "opus",
        "--effort",
        "high",
        "--tools",
        "Read",
        "--allowedTools",
        "Read",
        "--add-dir",
        str(samples[0].image_path.parent),
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
        build_prompt(samples, attached_images=False),
    ]

    started = time.monotonic()
    process = subprocess.run(
        command,
        cwd="/private/tmp",
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    elapsed = time.monotonic() - started
    log_path.write_text(
        "STDOUT:\n" + process.stdout + "\nSTDERR:\n" + process.stderr,
        encoding="utf-8",
    )
    combined_output = process.stdout + "\n" + process.stderr
    if process.returncode != 0:
        if "usage limit" in combined_output.lower():
            raise UsageLimitError(
                f"claude usage limit after {elapsed:.1f}s; see {log_path}",
                parse_usage_limit_retry_at(combined_output),
            )
        raise RuntimeError(
            f"claude exited {process.returncode} after {elapsed:.1f}s; see {log_path}"
        )
    try:
        wrapper = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise ValueError(f"claude returned invalid JSON; see {log_path}") from error
    payload = wrapper.get("structured_output") or wrapper.get("structuredOutput")
    if payload is None and isinstance(wrapper.get("result"), str):
        try:
            payload = json.loads(wrapper["result"])
        except json.JSONDecodeError as error:
            raise ValueError(f"claude result was not structured JSON; see {log_path}") from error
    predictions = validate_payload(payload, samples)
    write_json(temp_output, {"answers": predictions})
    os.replace(temp_output, batch_path)
    return predictions


def write_json(path: Path, payload: Any) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temp_path, path)


def collect_predictions(
    samples: list[Sample], batch_dir: Path, batch_size: int
) -> list[dict[str, str]]:
    collected: list[dict[str, str]] = []
    for start in range(0, len(samples), batch_size):
        batch = samples[start : start + batch_size]
        end = start + len(batch) - 1
        batch_path = batch_dir / f"batch_{start:04d}_{end:04d}.json"
        if not batch_path.is_file():
            raise FileNotFoundError(f"missing completed batch: {batch_path}")
        collected.extend(read_valid_batch(batch_path, batch))
    return collected


def write_submission(
    run_dir: Path, samples: list[Sample], predictions: list[dict[str, str]]
) -> tuple[Path, Path]:
    predictions_path = run_dir / "predictions.jsonl"
    predictions_text = "".join(
        json.dumps(prediction, ensure_ascii=False) + "\n" for prediction in predictions
    )
    predictions_path.write_text(predictions_text, encoding="utf-8")

    submission_path = run_dir / "submission.csv"
    with submission_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id", "label"])
        writer.writeheader()
        for sample, prediction in zip(samples, predictions, strict=True):
            if sample.sample_id != prediction["sample_id"]:
                raise ValueError("prediction order mismatch")
            writer.writerow({"sample_id": sample.sample_id, "label": prediction["label"]})
    return predictions_path, submission_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-csv", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("configs/codex_teacher_output_schema.json"),
    )
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--backend", choices=["codex", "claude"], default="codex")
    parser.add_argument("--model")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--max-usage-wait-seconds", type=int, default=21600)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.batch_size <= 32:
        raise SystemExit("--batch-size must be between 1 and 32")
    if args.max_attempts < 1:
        raise SystemExit("--max-attempts must be at least 1")

    csv_path = args.test_csv.resolve()
    image_root = args.image_root.resolve()
    schema_path = args.schema.resolve()
    run_dir = args.run_dir.resolve()
    all_samples = load_samples(csv_path, image_root)
    selected_samples = all_samples[: args.limit] if args.limit else all_samples
    if not selected_samples:
        raise SystemExit("no samples selected")
    run_dir.mkdir(parents=True, exist_ok=True)
    batch_dir = run_dir / "batches"
    batch_dir.mkdir(exist_ok=True)

    metadata_path = run_dir / "run_metadata.json"
    metadata = {
        "prompt_version": PROMPT_VERSION,
        "test_csv": str(csv_path),
        "test_csv_sha256": sha256_file(csv_path),
        "total_input_rows": len(all_samples),
        "selected_rows": len(selected_samples),
        "batch_size": args.batch_size,
        "model": args.model or "codex-default",
    }
    if metadata_path.is_file():
        existing_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if existing_metadata != metadata:
            raise SystemExit("run metadata differs; use a new --run-dir")
    else:
        write_json(metadata_path, metadata)

    started = time.monotonic()
    for start in range(0, len(selected_samples), args.batch_size):
        batch = selected_samples[start : start + args.batch_size]
        end = start + len(batch) - 1
        batch_path = batch_dir / f"batch_{start:04d}_{end:04d}.json"
        if batch_path.is_file():
            read_valid_batch(batch_path, batch)
            print(f"SKIP valid batch {start}-{end}", flush=True)
            continue
        last_error: Exception | None = None
        attempt = 1
        while attempt <= args.max_attempts:
            try:
                invoke = invoke_codex if args.backend == "codex" else invoke_claude
                invoke(
                    batch,
                    schema_path,
                    batch_path,
                    args.model,
                    args.timeout_seconds,
                    attempt,
                )
                print(f"OK batch {start}-{end} attempt={attempt}", flush=True)
                last_error = None
                break
            except UsageLimitError as error:
                last_error = error
                now = datetime.now().astimezone()
                retry_at = error.retry_at
                if retry_at is None:
                    raise SystemExit(f"batch {start}-{end} blocked: {error}") from error
                wait_seconds = max(0.0, (retry_at - now).total_seconds())
                if wait_seconds > args.max_usage_wait_seconds:
                    raise SystemExit(
                        f"batch {start}-{end} usage reset wait {wait_seconds:.0f}s exceeds "
                        f"--max-usage-wait-seconds"
                    ) from error
                print(
                    f"WAIT usage limit until {retry_at.isoformat()} "
                    f"({wait_seconds:.0f}s); completed through {start - 1}",
                    flush=True,
                )
                time.sleep(wait_seconds)
            except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
                last_error = error
                print(f"RETRY batch {start}-{end} attempt={attempt}: {error}", flush=True)
                attempt += 1
        if last_error is not None:
            raise SystemExit(f"batch {start}-{end} failed: {last_error}")

    predictions = collect_predictions(selected_samples, batch_dir, args.batch_size)
    predictions_path, submission_path = write_submission(
        run_dir, selected_samples, predictions
    )
    elapsed = time.monotonic() - started
    summary = {
        **metadata,
        "completed_rows": len(predictions),
        "elapsed_seconds_this_invocation": elapsed,
        "predictions_sha256": sha256_file(predictions_path),
        "submission_sha256": sha256_file(submission_path),
        "submission_ready": len(predictions) == len(all_samples) == 8500,
    }
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(predictions) != len(all_samples):
        print("Partial run only; submission.csv is not a complete competition submission.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
