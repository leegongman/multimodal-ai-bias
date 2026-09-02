"""Reasoner orchestration boundary."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from multimodal_bias.data_loader import load_test_records
from multimodal_bias.exceptions import ConfigurationError, InferenceError
from multimodal_bias.image_io import load_sample_images
from multimodal_bias.models.adapter import VisionLanguageModelAdapter, create_model_adapter
from multimodal_bias.prompting.templates import (
    DEFAULT_REASONER_PROMPT_PATH,
    build_reasoner_prompt,
    load_reasoner_prompt_template,
)
from multimodal_bias.schemas import (
    CompetitionConfig,
    ImageLoadReport,
    ImageLoadResult,
    ModelConfig,
    ModelGenerationRequest,
    ModelLoadMetadata,
    RawReasonerRecord,
    RawReasonerStatus,
    ReasonerPrompt,
    ReasonerRunResult,
    RunManifest,
    SampleRecord,
)

RAW_REASONER_FILENAME = "raw_reasoner.jsonl"
RAW_REASONER_PARTIAL_FILENAME = "raw_reasoner.partial.jsonl"
RAW_REASONER_FSYNC_INTERVAL = 25


@dataclass(frozen=True)
class PreparedReasonerInference:
    """Run-level inputs validated before run artifact creation."""

    records: tuple[SampleRecord, ...]
    image_report: ImageLoadReport
    adapter: VisionLanguageModelAdapter
    model_load_metadata: ModelLoadMetadata
    prompt_version: str


def prepare_reasoner_inference(
    config: CompetitionConfig,
    model_config: ModelConfig,
    *,
    prompt_template_path: Path | str = DEFAULT_REASONER_PROMPT_PATH,
) -> PreparedReasonerInference:
    """Validate run-level inputs and load the model before creating run artifacts."""

    prompt_template = load_reasoner_prompt_template(prompt_template_path)
    records = load_test_records(config.data_root, allow_missing_images=True)
    image_report = load_sample_images(records)
    adapter = create_model_adapter(model_config)
    model_load_metadata = adapter.load()

    return PreparedReasonerInference(
        records=records,
        image_report=image_report,
        adapter=adapter,
        model_load_metadata=model_load_metadata,
        prompt_version=prompt_template.version,
    )


def run_reasoner_inference(
    config: CompetitionConfig,
    model_config: ModelConfig,
    manifest: RunManifest,
    *,
    prompt_template_path: Path | str = DEFAULT_REASONER_PROMPT_PATH,
    prepared: PreparedReasonerInference | None = None,
) -> ReasonerRunResult:
    """Run first-pass Reasoner inference and preserve raw model output."""

    prepared_inputs = prepared or prepare_reasoner_inference(
        config,
        model_config,
        prompt_template_path=prompt_template_path,
    )
    records = prepared_inputs.records
    image_report = prepared_inputs.image_report

    raw_reasoner_path = manifest.run_dir / RAW_REASONER_FILENAME
    partial_raw_reasoner_path = manifest.run_dir / RAW_REASONER_PARTIAL_FILENAME
    generated_count = 0

    partial_raw_reasoner_path.unlink(missing_ok=True)
    with partial_raw_reasoner_path.open("w", encoding="utf-8") as jsonl_file:
        for index, (sample, image_result) in enumerate(
            zip(records, image_report.results, strict=True),
            start=1,
        ):
            record = _run_sample(
                sample=sample,
                image_result=image_result,
                manifest=manifest,
                prompt_template_path=prompt_template_path,
                adapter=prepared_inputs.adapter,
                model_load_metadata=prepared_inputs.model_load_metadata,
                prompt_version=prepared_inputs.prompt_version,
            )
            if record.status == "generated":
                generated_count += 1
            jsonl_file.write(json.dumps(_jsonable(record), ensure_ascii=False, sort_keys=True))
            jsonl_file.write("\n")
            jsonl_file.flush()
            if index == 1 or index % RAW_REASONER_FSYNC_INTERVAL == 0:
                os.fsync(jsonl_file.fileno())
        os.fsync(jsonl_file.fileno())
    partial_raw_reasoner_path.replace(raw_reasoner_path)

    total_samples = len(records)
    return ReasonerRunResult(
        manifest=manifest,
        raw_reasoner_path=raw_reasoner_path,
        total_samples=total_samples,
        generated_count=generated_count,
        failure_count=total_samples - generated_count,
    )


def _run_sample(
    *,
    sample: SampleRecord,
    image_result: ImageLoadResult,
    manifest: RunManifest,
    prompt_template_path: Path | str,
    adapter: VisionLanguageModelAdapter,
    model_load_metadata: ModelLoadMetadata,
    prompt_version: str,
) -> RawReasonerRecord:
    started_at = perf_counter()

    if image_result.status != "loaded":
        return _failure_record(
            manifest=manifest,
            sample=sample,
            image_result=image_result,
            prompt_version=prompt_version,
            status="image_failed",
            error_type="ImageLoadError",
            error_message=image_result.error_message
            or f"image load failed with status: {image_result.status}",
            elapsed_seconds=perf_counter() - started_at,
            model_load_metadata=model_load_metadata,
        )

    try:
        prompt = build_reasoner_prompt(sample, prompt_template_path)
    except ConfigurationError as exc:
        return _failure_record(
            manifest=manifest,
            sample=sample,
            image_result=image_result,
            prompt_version=prompt_version,
            status="prompt_failed",
            error=exc,
            elapsed_seconds=perf_counter() - started_at,
            model_load_metadata=model_load_metadata,
        )

    prompt_text = _join_prompt_text(prompt)
    try:
        result = adapter.generate(
            ModelGenerationRequest(
                prompt_text=prompt_text,
                image_bytes=image_result.image_bytes,
                image_format=image_result.image_format,
            )
        )
    except InferenceError as exc:
        return _failure_record(
            manifest=manifest,
            sample=sample,
            image_result=image_result,
            prompt_version=prompt.prompt_version,
            prompt_text=prompt_text,
            status="inference_failed",
            error=exc,
            elapsed_seconds=perf_counter() - started_at,
            model_load_metadata=model_load_metadata,
        )

    return RawReasonerRecord(
        run_id=manifest.run_id,
        sample_id=sample.sample_id,
        prompt_version=prompt.prompt_version,
        prompt_text=prompt_text,
        prompt_sha256=_text_sha256(prompt_text),
        image_path=image_result.image_path,
        image_status=image_result.status,
        image_sha256=_bytes_sha256(image_result.image_bytes),
        image_byte_count=_byte_count(image_result.image_bytes),
        image_format=image_result.image_format,
        raw_output=result.raw_text,
        generation_metadata=result.metadata,
        model_load_metadata=model_load_metadata,
        elapsed_seconds=perf_counter() - started_at,
        status="generated",
        error_type=None,
        error_message=None,
    )


def _failure_record(
    *,
    manifest: RunManifest,
    sample: SampleRecord,
    image_result: ImageLoadResult,
    prompt_version: str | None,
    prompt_text: str | None = None,
    status: RawReasonerStatus,
    elapsed_seconds: float,
    model_load_metadata: ModelLoadMetadata,
    error: Exception | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> RawReasonerRecord:
    return RawReasonerRecord(
        run_id=manifest.run_id,
        sample_id=sample.sample_id,
        prompt_version=prompt_version,
        prompt_text=prompt_text,
        prompt_sha256=_text_sha256(prompt_text),
        image_path=image_result.image_path,
        image_status=image_result.status,
        image_sha256=_bytes_sha256(image_result.image_bytes),
        image_byte_count=_byte_count(image_result.image_bytes),
        image_format=image_result.image_format,
        raw_output=None,
        generation_metadata=None,
        model_load_metadata=model_load_metadata,
        elapsed_seconds=elapsed_seconds,
        status=status,
        error_type=error_type or (type(error).__name__ if error is not None else None),
        error_message=error_message or (str(error) if error is not None else None),
    )


def _join_prompt_text(prompt: ReasonerPrompt) -> str:
    return f"{prompt.system_prompt}\n\n{prompt.user_prompt}"


def _text_sha256(value: str | None) -> str | None:
    return sha256(value.encode("utf-8")).hexdigest() if value is not None else None


def _bytes_sha256(value: bytes | None) -> str | None:
    return sha256(value).hexdigest() if value is not None else None


def _byte_count(value: bytes | None) -> int | None:
    return len(value) if value is not None else None


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value
