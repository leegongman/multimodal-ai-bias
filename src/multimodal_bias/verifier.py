"""Conditional verifier trigger boundary."""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from time import perf_counter

from multimodal_bias.exceptions import ConfigurationError, InferenceError, ParseError
from multimodal_bias.image_io import load_sample_images
from multimodal_bias.models.adapter import VisionLanguageModelAdapter, create_model_adapter
from multimodal_bias.parsing import parse_verifier_output
from multimodal_bias.prompting.guards import (
    EVIDENCE_TYPES,
    FORBIDDEN_SOLE_SUPPORT_CUES,
    REASONER_OUTPUT_SCHEMA_VERSION,
)
from multimodal_bias.prompting.templates import (
    DEFAULT_VERIFIER_PROMPT_PATH,
    build_verifier_prompt,
    load_verifier_prompt_template,
)
from multimodal_bias.schemas import (
    ImageLoadResult,
    ModelConfig,
    ModelGenerationMetadata,
    ModelGenerationRequest,
    ModelLoadMetadata,
    ParsedReasonerRecord,
    ReasonerLabel,
    SampleRecord,
    VerificationRecord,
    VerificationStatus,
    VerificationTrigger,
    VerificationTriggerDecision,
    VerificationTriggerReport,
    VerifierParseStatus,
    VerifierRunResult,
)

VERIFICATION_FILENAME = "verification.jsonl"

VERIFICATION_TRIGGER_NAMES: tuple[VerificationTrigger, ...] = (
    "invalid_parse",
    "low_confidence",
    "unsupported_evidence",
    "protected_attribute_risk",
    "appearance_only_reasoning",
    "ambiguous_visual_grounding",
    "reasoner_verifier_conflict",
)

VALID_PARSE_STATUSES = frozenset(
    {
        "valid",
        "source_failed",
        "missing_marker",
        "invalid_json",
        "invalid_schema",
        "invalid_label",
    }
)
VALID_LABELS = frozenset({"0", "1", "2"})
VALID_RISK_FLAGS = frozenset({"invalid_parse", "protected_attribute_risk"})
DECISIVE_EVIDENCE_TYPES = frozenset(
    {"stated_text_fact", "objective_visible_evidence", "elimination"}
)
PERSON_LABELS = frozenset({"0", "1"})
PUNCTUATION_PATTERN = re.compile(r"[^\w]+", re.UNICODE)


def _normalize_text(value: str) -> str:
    return " ".join(PUNCTUATION_PATTERN.sub(" ", value.casefold().replace("_", " ")).split())


def _normalized_cues(cues: tuple[str, ...]) -> tuple[str, ...]:
    normalized = (_normalize_text(cue) for cue in cues)
    return tuple(dict.fromkeys(cue for cue in normalized if cue))


APPEARANCE_ONLY_CUES = _normalized_cues(
    tuple(cue.replace("_", " ") for cue in FORBIDDEN_SOLE_SUPPORT_CUES)
    + (
        "appearance",
        "looks like",
        "expression",
        "posture",
        "clothing",
        "attractive",
        "attractiveness",
        "social background",
        "perceived gender",
        "gender",
        "race",
        "ethnicity",
        "age",
        "older",
        "younger",
        "body type",
        "stereotype",
    )
)
VAGUE_VISUAL_CUES = _normalized_cues(
    (
        "image shows",
        "photo shows",
        "picture shows",
        "visible scene",
        "scene points",
        "points to",
        "looks like",
        "looks",
        "appears",
        "seems",
        "visual impression",
    )
)
CONCRETE_VISUAL_GROUNDING_CUES = _normalized_cues(
    (
        "holding",
        "using",
        "reading",
        "writing",
        "speaking",
        "microphone",
        "badge",
        "name tag",
        "nametag",
        "uniform",
        "sign",
        "visible text",
        "written text",
        "caption",
        "tool",
        "book",
        "phone",
        "screen",
        "desk",
        "counter",
    )
)
NON_APPEARANCE_SUPPORT_CUES = _normalized_cues(
    CONCRETE_VISUAL_GROUNDING_CUES
    + (
        "context states",
        "context explicitly states",
        "question states",
        "answer text",
        "text states",
        "stated fact",
        "explicitly states",
        "according to",
        "written",
        "ruled out",
        "elimination",
        "opposite fact",
    )
)
NEGATED_VISUAL_CUES = _normalized_cues(
    tuple(
        f"{prefix} {cue}"
        for prefix in ("no", "not", "without", "unclear")
        for cue in CONCRETE_VISUAL_GROUNDING_CUES
    )
    + (
        "does not show",
        "is not visible",
        "are not visible",
    )
)


def detect_verification_triggers(
    record: ParsedReasonerRecord,
) -> VerificationTriggerDecision:
    """Classify one parsed Reasoner row into stable verifier trigger names."""

    _validate_identity(record)
    parse_status = record.parse_status
    if parse_status not in VALID_PARSE_STATUSES:
        raise ParseError(f"unsupported Reasoner parse_status: {parse_status!r}")
    _validate_risk_flags(record)

    triggers: set[VerificationTrigger] = set()
    if parse_status != "valid" or "invalid_parse" in record.risk_flags:
        triggers.add("invalid_parse")
        return _decision(record, triggers)

    parsed_label, evidence_summary, evidence_type, uncertainty_signal = _validated_valid_fields(
        record
    )

    if "protected_attribute_risk" in record.risk_flags:
        triggers.add("protected_attribute_risk")
    if parsed_label in PERSON_LABELS and uncertainty_signal:
        triggers.add("low_confidence")
    if _has_unsupported_evidence(
        parsed_label=parsed_label,
        evidence_type=evidence_type,
        uncertainty_signal=uncertainty_signal,
    ):
        triggers.add("unsupported_evidence")
    if _has_appearance_only_reasoning(evidence_summary):
        triggers.add("appearance_only_reasoning")
    if _has_ambiguous_visual_grounding(
        parsed_label=parsed_label,
        evidence_type=evidence_type,
        evidence_summary=evidence_summary,
    ):
        triggers.add("ambiguous_visual_grounding")

    return _decision(record, triggers)


def detect_verification_trigger_report(
    records: Sequence[ParsedReasonerRecord],
) -> VerificationTriggerReport:
    """Classify ordered parsed Reasoner rows and aggregate trigger counts."""

    if (
        isinstance(records, ParsedReasonerRecord)
        or isinstance(records, str)
        or not isinstance(records, Sequence)
    ):
        raise ParseError("records must be a sequence of ParsedReasonerRecord objects")

    decisions = tuple(detect_verification_triggers(record) for record in records)
    per_trigger_counts = dict.fromkeys(VERIFICATION_TRIGGER_NAMES, 0)
    for decision in decisions:
        for trigger in decision.triggers:
            per_trigger_counts[trigger] += 1
    return VerificationTriggerReport(
        decisions=decisions,
        total_samples=len(decisions),
        triggered_sample_count=sum(decision.requires_verification for decision in decisions),
        per_trigger_counts=per_trigger_counts,
    )


def run_conditional_verification(
    records: Sequence[ParsedReasonerRecord],
    samples: Sequence[SampleRecord],
    run_dir: Path | str,
    model_config: ModelConfig,
    *,
    prompt_template_path: Path | str = DEFAULT_VERIFIER_PROMPT_PATH,
    adapter: VisionLanguageModelAdapter | None = None,
) -> VerifierRunResult:
    """Run one local Verifier pass for triggered samples and publish JSONL."""

    if isinstance(samples, (str, bytes)) or not isinstance(samples, Sequence):
        raise ParseError("samples must be a sequence of SampleRecord objects")
    if not records:
        raise ParseError("conditional verification requires at least one Reasoner record")
    if len(records) != len(samples):
        raise ParseError("Reasoner record and sample counts must match")
    if any(not isinstance(sample, SampleRecord) for sample in samples):
        raise ParseError("samples must contain only SampleRecord objects")

    report = detect_verification_trigger_report(records)
    expected_ids = tuple(record.sample_id for record in records)
    if len(set(expected_ids)) != len(expected_ids):
        raise ParseError("Reasoner records contain duplicate sample_id values")
    sample_ids = tuple(sample.sample_id for sample in samples)
    if sample_ids != expected_ids:
        raise ParseError("Reasoner records and samples must have identical ordered sample IDs")
    run_ids = {record.run_id for record in records}
    if len(run_ids) != 1:
        raise ParseError("Reasoner records must contain exactly one run_id")
    run_id = next(iter(run_ids))

    run_path = _validate_verification_output_path(run_dir, run_id)
    verification_path = run_path / VERIFICATION_FILENAME
    template = load_verifier_prompt_template(prompt_template_path)

    triggered_pairs = tuple(
        (sample, decision)
        for sample, decision in zip(samples, report.decisions, strict=True)
        if decision.requires_verification
    )
    image_results: dict[str, ImageLoadResult] = {}
    adapter_instance: VisionLanguageModelAdapter | None = None
    model_load_metadata: ModelLoadMetadata | None = None
    if triggered_pairs:
        triggered_samples = tuple(sample for sample, _ in triggered_pairs)
        image_report = load_sample_images(triggered_samples)
        image_results = {result.sample_id: result for result in image_report.results}
        adapter_instance = adapter or create_model_adapter(model_config)
        model_load_metadata = adapter_instance.load()

    verification_records: list[VerificationRecord] = []
    for record, sample, decision in zip(records, samples, report.decisions, strict=True):
        if not decision.requires_verification:
            verification_records.append(_skipped_record(record, template.version))
            continue
        assert adapter_instance is not None
        assert model_load_metadata is not None
        verification_records.append(
            _run_verifier_sample(
                record=record,
                sample=sample,
                decision=decision,
                image_result=image_results[sample.sample_id],
                adapter=adapter_instance,
                model_load_metadata=model_load_metadata,
                prompt_template_path=prompt_template_path,
                prompt_version=template.version,
            )
        )

    final_records = tuple(verification_records)
    _write_verification_artifact(verification_path, final_records)
    verified_count = sum(record.status == "verified" for record in final_records)
    skipped_count = sum(record.status == "skipped_not_triggered" for record in final_records)
    return VerifierRunResult(
        verification_path=verification_path,
        records=final_records,
        total_samples=len(final_records),
        triggered_count=report.triggered_sample_count,
        verified_count=verified_count,
        skipped_count=skipped_count,
        failed_count=report.triggered_sample_count - verified_count,
    )


def _run_verifier_sample(
    *,
    record: ParsedReasonerRecord,
    sample: SampleRecord,
    decision: VerificationTriggerDecision,
    image_result: ImageLoadResult,
    adapter: VisionLanguageModelAdapter,
    model_load_metadata: ModelLoadMetadata,
    prompt_template_path: Path | str,
    prompt_version: str,
) -> VerificationRecord:
    started_at = perf_counter()
    if image_result.status != "loaded":
        return _failed_verification_record(
            record=record,
            decision=decision,
            prompt_version=prompt_version,
            image_result=image_result,
            model_load_metadata=model_load_metadata,
            elapsed_seconds=perf_counter() - started_at,
            status="image_failed",
            error_type="ImageLoadError",
            error_message=image_result.error_message,
        )

    try:
        prompt = build_verifier_prompt(
            sample,
            record,
            decision.triggers,
            prompt_template_path,
        )
    except ConfigurationError as exc:
        return _failed_verification_record(
            record=record,
            decision=decision,
            prompt_version=prompt_version,
            image_result=image_result,
            model_load_metadata=model_load_metadata,
            elapsed_seconds=perf_counter() - started_at,
            status="prompt_failed",
            error=exc,
        )

    try:
        generation = adapter.generate(
            ModelGenerationRequest(
                prompt_text=f"{prompt.system_prompt}\n\n{prompt.user_prompt}",
                image_bytes=image_result.image_bytes,
                image_format=image_result.image_format,
            )
        )
    except InferenceError as exc:
        return _failed_verification_record(
            record=record,
            decision=decision,
            prompt_version=prompt.prompt_version,
            image_result=image_result,
            model_load_metadata=model_load_metadata,
            elapsed_seconds=perf_counter() - started_at,
            status="inference_failed",
            error=exc,
        )

    parsed = parse_verifier_output(generation.raw_text)
    if parsed.output is None:
        return _failed_verification_record(
            record=record,
            decision=decision,
            prompt_version=prompt.prompt_version,
            image_result=image_result,
            model_load_metadata=model_load_metadata,
            elapsed_seconds=perf_counter() - started_at,
            status="parse_failed",
            raw_output=_safe_utf8_text(generation.raw_text),
            generation_metadata=generation.metadata,
            verifier_parse_status=parsed.parse_status,
            error_type="ParseError",
            error_message=parsed.parse_error,
        )

    output = parsed.output
    triggers = set(decision.triggers)
    if record.parsed_label is not None and record.parsed_label != output.label:
        triggers.add("reasoner_verifier_conflict")
    ordered_triggers = tuple(
        trigger for trigger in VERIFICATION_TRIGGER_NAMES if trigger in triggers
    )
    return VerificationRecord(
        run_id=record.run_id,
        sample_id=record.sample_id,
        prompt_version=prompt.prompt_version,
        triggers=ordered_triggers,
        requires_verification=True,
        before_label=record.parsed_label,
        raw_verifier_output=generation.raw_text,
        after_label=output.label,
        verifier_reason=output.reason,
        verifier_evidence_type=output.evidence_type,
        reasoner_defect_found=output.reasoner_defect_found,
        objective_support=output.objective_support,
        image_status=image_result.status,
        verifier_parse_status="valid",
        generation_metadata=generation.metadata,
        model_load_metadata=model_load_metadata,
        elapsed_seconds=perf_counter() - started_at,
        status="verified",
        error_type=None,
        error_message=None,
    )


def _skipped_record(
    record: ParsedReasonerRecord,
    prompt_version: str,
) -> VerificationRecord:
    return VerificationRecord(
        run_id=record.run_id,
        sample_id=record.sample_id,
        prompt_version=prompt_version,
        triggers=(),
        requires_verification=False,
        before_label=record.parsed_label,
        raw_verifier_output=None,
        after_label=None,
        verifier_reason=None,
        verifier_evidence_type=None,
        reasoner_defect_found=None,
        objective_support=None,
        image_status=None,
        verifier_parse_status=None,
        generation_metadata=None,
        model_load_metadata=None,
        elapsed_seconds=0.0,
        status="skipped_not_triggered",
        error_type=None,
        error_message=None,
    )


def _failed_verification_record(
    *,
    record: ParsedReasonerRecord,
    decision: VerificationTriggerDecision,
    prompt_version: str,
    image_result: ImageLoadResult,
    model_load_metadata: ModelLoadMetadata,
    elapsed_seconds: float,
    status: VerificationStatus,
    raw_output: str | None = None,
    generation_metadata: ModelGenerationMetadata | None = None,
    verifier_parse_status: VerifierParseStatus | None = None,
    error: Exception | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> VerificationRecord:
    return VerificationRecord(
        run_id=record.run_id,
        sample_id=record.sample_id,
        prompt_version=prompt_version,
        triggers=decision.triggers,
        requires_verification=True,
        before_label=record.parsed_label,
        raw_verifier_output=raw_output,
        after_label=None,
        verifier_reason=None,
        verifier_evidence_type=None,
        reasoner_defect_found=None,
        objective_support=None,
        image_status=image_result.status,
        verifier_parse_status=verifier_parse_status,
        generation_metadata=generation_metadata,
        model_load_metadata=model_load_metadata,
        elapsed_seconds=elapsed_seconds,
        status=status,
        error_type=error_type or (type(error).__name__ if error is not None else None),
        error_message=_safe_utf8_text(error_message or (str(error) if error is not None else ""))
        or None,
    )


def _validate_verification_output_path(run_dir: Path | str, run_id: str) -> Path:
    try:
        run_path = Path(run_dir)
        run_stat = run_path.lstat()
    except (OSError, TypeError, ValueError) as exc:
        raise ParseError(f"verification run directory is invalid: {run_dir}: {exc}") from exc
    if stat.S_ISLNK(run_stat.st_mode) or not stat.S_ISDIR(run_stat.st_mode):
        raise ParseError(f"verification run directory must be a regular directory: {run_path}")
    if run_path.name != run_id:
        raise ParseError(
            f"verification run directory name {run_path.name!r} does not match run_id {run_id!r}"
        )
    output_path = run_path / VERIFICATION_FILENAME
    if os.path.lexists(output_path):
        raise ParseError(f"verification artifact already exists: {output_path}")
    return run_path


def _write_verification_artifact(
    output_path: Path,
    records: tuple[VerificationRecord, ...],
) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as jsonl_file:
            temp_path = Path(jsonl_file.name)
            for record in records:
                jsonl_file.write(
                    json.dumps(
                        _jsonable(record),
                        ensure_ascii=False,
                        sort_keys=True,
                        allow_nan=False,
                    )
                )
                jsonl_file.write("\n")
        try:
            os.link(temp_path, output_path)
        except FileExistsError as exc:
            raise ParseError(f"verification artifact already exists: {output_path}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _safe_utf8_text(value: str) -> str:
    return value.encode("utf-8", errors="backslashreplace").decode("utf-8")


def _validate_identity(record: ParsedReasonerRecord) -> None:
    if not isinstance(record, ParsedReasonerRecord):
        raise ParseError("trigger detection requires ParsedReasonerRecord input")
    if (
        record.schema_version == REASONER_OUTPUT_SCHEMA_VERSION
        or record.uncertainty_option_index is not None
    ):
        raise ParseError(
            "legacy Verifier is not compatible with Reasoner v3 lineage; "
            "complete Story 3.1 before enabling verification"
        )
    for field_name, value in (("run_id", record.run_id), ("sample_id", record.sample_id)):
        if not isinstance(value, str) or not value.strip():
            raise ParseError(f"{field_name} must be a non-empty string")
        _require_utf8(value, field_name)


def _validate_risk_flags(record: ParsedReasonerRecord) -> None:
    if not isinstance(record.risk_flags, tuple) or any(
        not isinstance(flag, str) or flag not in VALID_RISK_FLAGS for flag in record.risk_flags
    ):
        raise ParseError(f"unsupported Reasoner risk_flags for sample {record.sample_id}")


def _validated_valid_fields(
    record: ParsedReasonerRecord,
) -> tuple[ReasonerLabel, str, str, bool]:
    parsed_label = record.parsed_label
    evidence_summary = record.evidence_summary
    evidence_type = record.evidence_type
    uncertainty_signal = record.uncertainty_signal

    if not isinstance(parsed_label, str) or parsed_label not in VALID_LABELS:
        raise ParseError(f"valid parsed row {record.sample_id} is missing a valid label")
    if not isinstance(evidence_summary, str) or not evidence_summary.strip():
        raise ParseError(f"valid parsed row {record.sample_id} is missing evidence")
    _require_utf8(evidence_summary, f"valid parsed row {record.sample_id} evidence")
    if not isinstance(evidence_type, str) or evidence_type not in EVIDENCE_TYPES:
        raise ParseError(f"valid parsed row {record.sample_id} has unsupported evidence_type")
    if type(uncertainty_signal) is not bool:
        raise ParseError(f"valid parsed row {record.sample_id} has invalid uncertainty_signal")

    return parsed_label, evidence_summary, evidence_type, uncertainty_signal


def _has_unsupported_evidence(
    *,
    parsed_label: str,
    evidence_type: str,
    uncertainty_signal: bool,
) -> bool:
    if parsed_label in PERSON_LABELS and evidence_type == "insufficient_evidence":
        return True
    if parsed_label == "2" and evidence_type in DECISIVE_EVIDENCE_TYPES:
        return True
    if parsed_label == "2" and not uncertainty_signal:
        return True
    return parsed_label in PERSON_LABELS and uncertainty_signal


def _has_appearance_only_reasoning(evidence_summary: str) -> bool:
    normalized = _normalize_text(evidence_summary)
    if not any(_contains_phrase(normalized, cue) for cue in APPEARANCE_ONLY_CUES):
        return False
    return not _has_non_appearance_support(normalized)


def _has_ambiguous_visual_grounding(
    *,
    parsed_label: str,
    evidence_type: str,
    evidence_summary: str,
) -> bool:
    if parsed_label not in PERSON_LABELS or evidence_type != "objective_visible_evidence":
        return False
    normalized = _normalize_text(evidence_summary)
    if _has_positive_visual_grounding(normalized):
        return False
    return True


def _has_non_appearance_support(normalized_text: str) -> bool:
    return any(_contains_phrase(normalized_text, cue) for cue in NON_APPEARANCE_SUPPORT_CUES)


def _has_positive_visual_grounding(normalized_text: str) -> bool:
    return any(
        _contains_phrase(normalized_text, cue) and not _is_negated_visual_cue(normalized_text, cue)
        for cue in CONCRETE_VISUAL_GROUNDING_CUES
    )


def _is_negated_visual_cue(normalized_text: str, cue: str) -> bool:
    if any(_contains_phrase(normalized_text, negated) for negated in _negated_forms_for(cue)):
        return True
    return any(
        _contains_phrase(normalized_text, prefix) for prefix in ("no", "not", "without")
    ) and _contains_phrase(normalized_text, f"or {cue} is visible")


def _negated_forms_for(cue: str) -> tuple[str, ...]:
    return tuple(
        negated
        for negated in NEGATED_VISUAL_CUES
        if negated.endswith(f" {cue}")
        or negated in {"does not show", "is not visible", "are not visible"}
    )


def _decision(
    record: ParsedReasonerRecord,
    triggers: set[VerificationTrigger],
) -> VerificationTriggerDecision:
    ordered_triggers = tuple(
        trigger for trigger in VERIFICATION_TRIGGER_NAMES if trigger in triggers
    )
    return VerificationTriggerDecision(
        run_id=record.run_id,
        sample_id=record.sample_id,
        parsed_label=record.parsed_label,
        parse_status=record.parse_status,
        triggers=ordered_triggers,
        requires_verification=bool(ordered_triggers),
    )


def _contains_phrase(normalized_text: str, normalized_phrase: str) -> bool:
    phrase = _normalize_text(normalized_phrase)
    return bool(phrase) and f" {phrase} " in f" {normalized_text} "


def _require_utf8(value: str, field_name: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ParseError(f"{field_name} contains invalid Unicode data") from exc
