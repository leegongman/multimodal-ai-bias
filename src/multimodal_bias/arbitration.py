"""Final-label arbitration boundary."""

from __future__ import annotations

import json
import math
import os
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from multimodal_bias.exceptions import SubmissionFormatError
from multimodal_bias.prompting.guards import EVIDENCE_TYPES, REASONER_OUTPUT_SCHEMA_VERSION
from multimodal_bias.schemas import (
    EvidenceType,
    FinalPrediction,
    ImageLoadStatus,
    ModelGenerationMetadata,
    ModelLoadMetadata,
    ParsedReasonerRecord,
    ReasonerLabel,
    VerificationRecord,
    VerificationStatus,
    VerificationTrigger,
    VerifierParseStatus,
)

VERIFICATION_FILENAME = "verification.jsonl"

VALID_LABELS = frozenset({"0", "1", "2"})
VALID_SOURCE_SUPPORT_EVIDENCE = frozenset(
    {"stated_text_fact", "objective_visible_evidence", "elimination"}
)
VALID_TRIGGERS = (
    "invalid_parse",
    "low_confidence",
    "unsupported_evidence",
    "protected_attribute_risk",
    "appearance_only_reasoning",
    "ambiguous_visual_grounding",
    "reasoner_verifier_conflict",
)
VALID_STATUSES = frozenset(
    {
        "verified",
        "skipped_not_triggered",
        "image_failed",
        "prompt_failed",
        "inference_failed",
        "parse_failed",
    }
)
VALID_IMAGE_STATUSES = frozenset({"loaded", "missing", "unreadable", "corrupt"})
VALID_VERIFIER_PARSE_STATUSES = frozenset(
    {"valid", "missing_marker", "invalid_json", "invalid_schema", "invalid_label"}
)
VERIFICATION_FIELDNAMES = (
    "run_id",
    "sample_id",
    "prompt_version",
    "triggers",
    "requires_verification",
    "before_label",
    "raw_verifier_output",
    "after_label",
    "verifier_reason",
    "verifier_evidence_type",
    "reasoner_defect_found",
    "objective_support",
    "image_status",
    "verifier_parse_status",
    "generation_metadata",
    "model_load_metadata",
    "elapsed_seconds",
    "status",
    "error_type",
    "error_message",
)
TRIGGER_ORDER = {trigger: index for index, trigger in enumerate(VALID_TRIGGERS)}


def read_verification_artifact(
    verification_path: Path | str,
    *,
    expected_run_id: str,
    expected_sample_ids: Sequence[str],
) -> tuple[VerificationRecord, ...]:
    """Read a strict Story 3.2 verification JSONL artifact."""

    expected_ids = _validate_expected_context(expected_run_id, expected_sample_ids)
    path = _validate_verification_path(verification_path)

    rows: list[VerificationRecord] = []
    seen: set[str] = set()
    try:
        with _open_utf8_text_no_follow(path, "verification artifact") as jsonl_file:
            for row_number, line in enumerate(jsonl_file, start=1):
                if not line.strip():
                    raise SubmissionFormatError(
                        f"verification artifact contains blank logical record {row_number}"
                    )
                payload = _loads_json_object(line, row_number)
                record = _verification_record_from_payload(payload, row_number)
                if record.run_id != expected_run_id:
                    raise SubmissionFormatError(
                        f"verification row {row_number} run_id does not match expected run_id"
                    )
                if record.sample_id in seen:
                    raise SubmissionFormatError(
                        f"verification artifact has duplicate sample_id: {record.sample_id}"
                    )
                seen.add(record.sample_id)
                rows.append(record)
    except SubmissionFormatError:
        raise
    except UnicodeDecodeError as exc:
        raise SubmissionFormatError(
            f"verification artifact is not valid UTF-8: {path}: {exc}"
        ) from exc
    except OSError as exc:
        raise SubmissionFormatError(
            f"verification artifact could not be read: {path}: {exc}"
        ) from exc

    if not rows:
        raise SubmissionFormatError(f"verification artifact has no data rows: {path}")

    actual_ids = tuple(record.sample_id for record in rows)
    if actual_ids != expected_ids:
        raise SubmissionFormatError(
            "verification ordered sample IDs do not match the official test set: "
            f"expected_count={len(expected_ids)} actual_count={len(actual_ids)}"
        )
    return tuple(rows)


def arbitrate_final_predictions(
    reasoner_records: Sequence[ParsedReasonerRecord],
    verification_records: Sequence[VerificationRecord] | None = None,
) -> tuple[FinalPrediction, ...]:
    """Select final labels through explicit Reasoner/Verifier arbitration."""

    records = _validate_reasoner_records(reasoner_records)
    verifications = _validate_optional_verification_records(records, verification_records)

    predictions: list[FinalPrediction] = []
    for index, record in enumerate(records):
        verification = verifications[index] if verifications is not None else None
        predictions.append(_arbitrate_one(record, verification))
    return tuple(predictions)


def _arbitrate_one(
    reasoner: ParsedReasonerRecord,
    verification: VerificationRecord | None,
) -> FinalPrediction:
    valid_reasoner_label = _valid_reasoner_label(reasoner)

    if verification is None:
        if valid_reasoner_label is not None:
            return _prediction(
                reasoner,
                valid_reasoner_label,
                "reasoner",
                "validated_reasoner_output",
            )
        raise SubmissionFormatError(f"sample {reasoner.sample_id} has no valid generated candidate")

    if verification.status == "skipped_not_triggered":
        if valid_reasoner_label is not None:
            return _prediction(
                reasoner,
                valid_reasoner_label,
                "reasoner",
                "validated_reasoner_output",
            )
        raise SubmissionFormatError(f"sample {reasoner.sample_id} has no valid generated candidate")

    if verification.status != "verified":
        if valid_reasoner_label is not None:
            return _prediction(
                reasoner,
                valid_reasoner_label,
                "reasoner",
                "verifier_no_usable_support_keep_reasoner",
            )
        raise SubmissionFormatError(f"sample {reasoner.sample_id} has no valid generated candidate")

    if verification.reasoner_defect_found is False:
        if valid_reasoner_label is not None:
            return _prediction(
                reasoner,
                valid_reasoner_label,
                "reasoner",
                "verifier_no_concrete_defect_keep_reasoner",
            )
        if _verifier_supports_person_label(verification):
            return _prediction(
                reasoner,
                cast(ReasonerLabel, verification.after_label),
                "verifier",
                "invalid_reasoner_recovered_with_objective_verifier",
            )
        raise SubmissionFormatError(f"sample {reasoner.sample_id} has no valid generated candidate")

    if _verifier_supports_person_label(verification):
        if valid_reasoner_label == verification.after_label:
            return _prediction(
                reasoner,
                valid_reasoner_label,
                "reasoner",
                "verifier_reaffirmed_reasoner_with_objective_support",
            )
        return _prediction(
            reasoner,
            cast(ReasonerLabel, verification.after_label),
            "verifier",
            "verifier_concrete_defect_with_objective_support",
        )

    if verification.after_label == "2" and not _reasoner_supports_person_label(reasoner):
        return _prediction(
            reasoner,
            "2",
            "arbitration",
            "both_outputs_lack_objective_support",
        )

    if valid_reasoner_label is not None:
        return _prediction(
            reasoner,
            valid_reasoner_label,
            "reasoner",
            "verifier_no_usable_support_keep_reasoner",
        )

    raise SubmissionFormatError(f"sample {reasoner.sample_id} has no valid generated candidate")


def _prediction(
    reasoner: ParsedReasonerRecord,
    label: ReasonerLabel,
    source_stage: str,
    decision_reason: str,
) -> FinalPrediction:
    return FinalPrediction(
        run_id=reasoner.run_id,
        sample_id=reasoner.sample_id,
        final_label=label,
        source_stage=source_stage,  # type: ignore[arg-type]
        decision_reason=decision_reason,
    )


def _valid_reasoner_label(record: ParsedReasonerRecord) -> ReasonerLabel | None:
    if record.parse_status != "valid" or record.parsed_label not in VALID_LABELS:
        return None
    return cast(ReasonerLabel, record.parsed_label)


def _reasoner_supports_person_label(record: ParsedReasonerRecord) -> bool:
    return (
        record.parse_status == "valid"
        and record.parsed_label in {"0", "1"}
        and record.evidence_type in VALID_SOURCE_SUPPORT_EVIDENCE
        and record.uncertainty_signal is False
        and bool(record.evidence_summary and record.evidence_summary.strip())
    )


def _verifier_supports_person_label(record: VerificationRecord) -> bool:
    return (
        record.status == "verified"
        and record.after_label in {"0", "1"}
        and record.reasoner_defect_found is True
        and record.objective_support is True
        and record.verifier_evidence_type in VALID_SOURCE_SUPPORT_EVIDENCE
        and bool(record.verifier_reason and record.verifier_reason.strip())
    )


def _validate_reasoner_records(
    reasoner_records: Sequence[ParsedReasonerRecord],
) -> tuple[ParsedReasonerRecord, ...]:
    if not isinstance(reasoner_records, Sequence) or isinstance(reasoner_records, (str, bytes)):
        raise SubmissionFormatError("Reasoner records must be a sequence")
    records = tuple(reasoner_records)
    if not records:
        raise SubmissionFormatError("Reasoner records must not be empty")
    seen: set[str] = set()
    run_id = records[0].run_id
    for index, record in enumerate(records):
        if not isinstance(record, ParsedReasonerRecord):
            raise SubmissionFormatError(f"Reasoner record at index {index} has invalid type")
        if (
            record.schema_version == REASONER_OUTPUT_SCHEMA_VERSION
            or record.uncertainty_option_index is not None
        ):
            raise SubmissionFormatError(
                "legacy arbitration is not compatible with Reasoner v3 lineage; "
                "complete Stories 3.1-3.3 before enabling verification arbitration"
            )
        if record.run_id != run_id:
            raise SubmissionFormatError("Reasoner records must share one run_id")
        _require_text(record.run_id, f"Reasoner record {index} run_id")
        _require_text(record.sample_id, f"Reasoner record {index} sample_id")
        if record.sample_id in seen:
            raise SubmissionFormatError(
                f"Reasoner records contain duplicate sample_id: {record.sample_id}"
            )
        seen.add(record.sample_id)
    return records


def _validate_optional_verification_records(
    reasoner_records: tuple[ParsedReasonerRecord, ...],
    verification_records: Sequence[VerificationRecord] | None,
) -> tuple[VerificationRecord, ...] | None:
    if verification_records is None:
        return None
    if not isinstance(verification_records, Sequence) or isinstance(
        verification_records, (str, bytes)
    ):
        raise SubmissionFormatError("Verification records must be a sequence")
    records = tuple(verification_records)
    reasoner_ids = tuple(record.sample_id for record in reasoner_records)
    verification_ids = tuple(record.sample_id for record in records)
    if verification_ids != reasoner_ids:
        raise SubmissionFormatError(
            "verification ordered sample IDs do not match parsed Reasoner rows: "
            f"expected_count={len(reasoner_ids)} actual_count={len(verification_ids)}"
        )
    seen: set[str] = set()
    for index, (reasoner, verification) in enumerate(zip(reasoner_records, records, strict=True)):
        if not isinstance(verification, VerificationRecord):
            raise SubmissionFormatError(f"Verification record at index {index} has invalid type")
        if verification.run_id != reasoner.run_id:
            raise SubmissionFormatError(
                f"Verification record {index} run_id does not match Reasoner run_id"
            )
        if verification.before_label != reasoner.parsed_label:
            raise SubmissionFormatError(
                f"Verification record {index} before_label does not match Reasoner label"
            )
        if verification.sample_id in seen:
            raise SubmissionFormatError(
                f"Verification records contain duplicate sample_id: {verification.sample_id}"
            )
        seen.add(verification.sample_id)
    return records


def _validate_expected_context(
    expected_run_id: str,
    expected_sample_ids: Sequence[str],
) -> tuple[str, ...]:
    _require_text(expected_run_id, "expected run_id")
    if not isinstance(expected_sample_ids, Sequence) or isinstance(
        expected_sample_ids, (str, bytes)
    ):
        raise SubmissionFormatError("expected sample IDs must be a sequence of strings")
    expected_ids = tuple(expected_sample_ids)
    if not expected_ids:
        raise SubmissionFormatError("expected sample IDs must not be empty")
    seen: set[str] = set()
    for index, sample_id in enumerate(expected_ids):
        _require_text(sample_id, f"expected sample ID at index {index}")
        if sample_id in seen:
            raise SubmissionFormatError(f"expected sample IDs contain duplicate value: {sample_id}")
        seen.add(sample_id)
    return expected_ids


def _validate_verification_path(path_like: Path | str) -> Path:
    path = Path(path_like)
    if path.name != VERIFICATION_FILENAME:
        raise SubmissionFormatError(
            f"verification artifact must use canonical filename {VERIFICATION_FILENAME}"
        )
    try:
        link_stat = path.lstat()
    except OSError as exc:
        raise SubmissionFormatError(f"verification artifact does not exist: {path}: {exc}") from exc
    if stat.S_ISLNK(link_stat.st_mode):
        raise SubmissionFormatError(f"verification artifact must not be a symlink: {path}")
    if not stat.S_ISREG(link_stat.st_mode):
        raise SubmissionFormatError(f"verification artifact must be a regular file: {path}")
    return path


def _open_utf8_text_no_follow(path: Path, artifact_name: str):
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        file_descriptor = os.open(path, flags)
    except OSError as exc:
        raise SubmissionFormatError(f"{artifact_name} could not be read: {path}: {exc}") from exc

    try:
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise SubmissionFormatError(f"{artifact_name} must be a regular file: {path}")
        return open(file_descriptor, encoding="utf-8", closefd=True)
    except Exception:
        os.close(file_descriptor)
        raise


def _loads_json_object(raw_line: str, row_number: int) -> dict[str, object]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"unsupported JSON constant {value}")

    def object_pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            raw_line,
            object_pairs_hook=object_pairs_hook,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise SubmissionFormatError(
            f"verification row {row_number} is malformed JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SubmissionFormatError(f"verification row {row_number} must be a JSON object")
    return payload


def _verification_record_from_payload(
    payload: dict[str, object],
    row_number: int,
) -> VerificationRecord:
    actual_keys = tuple(payload.keys())
    if set(actual_keys) != set(VERIFICATION_FIELDNAMES):
        raise SubmissionFormatError(
            f"verification row {row_number} fields must be exactly: "
            f"{', '.join(VERIFICATION_FIELDNAMES)}"
        )

    run_id = _required_text(payload["run_id"], row_number, "run_id")
    sample_id = _required_text(payload["sample_id"], row_number, "sample_id")
    prompt_version = _required_text(payload["prompt_version"], row_number, "prompt_version")
    triggers = _parse_triggers(payload["triggers"], row_number)
    requires_verification = _required_bool(
        payload["requires_verification"], row_number, "requires_verification"
    )
    before_label = _optional_label(payload["before_label"], row_number, "before_label")
    raw_verifier_output = _optional_text(
        payload["raw_verifier_output"], row_number, "raw_verifier_output"
    )
    after_label = _optional_label(payload["after_label"], row_number, "after_label")
    verifier_reason = _optional_text(payload["verifier_reason"], row_number, "verifier_reason")
    verifier_evidence_type = _optional_evidence_type(
        payload["verifier_evidence_type"], row_number, "verifier_evidence_type"
    )
    reasoner_defect_found = _optional_bool(
        payload["reasoner_defect_found"], row_number, "reasoner_defect_found"
    )
    objective_support = _optional_bool(
        payload["objective_support"], row_number, "objective_support"
    )
    image_status = _optional_image_status(payload["image_status"], row_number)
    verifier_parse_status = _optional_verifier_parse_status(
        payload["verifier_parse_status"], row_number
    )
    generation_metadata = _parse_generation_metadata(payload["generation_metadata"], row_number)
    model_load_metadata = _parse_model_load_metadata(payload["model_load_metadata"], row_number)
    elapsed_seconds = _required_nonnegative_float(
        payload["elapsed_seconds"], row_number, "elapsed_seconds"
    )
    status = _required_status(payload["status"], row_number)
    error_type = _optional_text(payload["error_type"], row_number, "error_type")
    error_message = _optional_text(payload["error_message"], row_number, "error_message")

    _validate_status_contract(
        row_number=row_number,
        status=status,
        triggers=triggers,
        requires_verification=requires_verification,
        raw_verifier_output=raw_verifier_output,
        after_label=after_label,
        verifier_reason=verifier_reason,
        verifier_evidence_type=verifier_evidence_type,
        reasoner_defect_found=reasoner_defect_found,
        objective_support=objective_support,
        image_status=image_status,
        verifier_parse_status=verifier_parse_status,
        error_type=error_type,
        error_message=error_message,
    )

    return VerificationRecord(
        run_id=run_id,
        sample_id=sample_id,
        prompt_version=prompt_version,
        triggers=triggers,
        requires_verification=requires_verification,
        before_label=before_label,
        raw_verifier_output=raw_verifier_output,
        after_label=after_label,
        verifier_reason=verifier_reason,
        verifier_evidence_type=verifier_evidence_type,
        reasoner_defect_found=reasoner_defect_found,
        objective_support=objective_support,
        image_status=image_status,
        verifier_parse_status=verifier_parse_status,
        generation_metadata=generation_metadata,
        model_load_metadata=model_load_metadata,
        elapsed_seconds=elapsed_seconds,
        status=status,
        error_type=error_type,
        error_message=error_message,
    )


def _validate_status_contract(
    *,
    row_number: int,
    status: VerificationStatus,
    triggers: tuple[VerificationTrigger, ...],
    requires_verification: bool,
    raw_verifier_output: str | None,
    after_label: ReasonerLabel | None,
    verifier_reason: str | None,
    verifier_evidence_type: EvidenceType | None,
    reasoner_defect_found: bool | None,
    objective_support: bool | None,
    image_status: ImageLoadStatus | None,
    verifier_parse_status: VerifierParseStatus | None,
    error_type: str | None,
    error_message: str | None,
) -> None:
    if status == "skipped_not_triggered":
        if requires_verification:
            raise SubmissionFormatError(
                f"verification row {row_number} requires_verification is invalid for skipped row"
            )
        if triggers:
            raise SubmissionFormatError(f"verification row {row_number} triggers must be empty")
        if any(
            value is not None
            for value in (
                raw_verifier_output,
                after_label,
                verifier_reason,
                verifier_evidence_type,
                reasoner_defect_found,
                objective_support,
                image_status,
                verifier_parse_status,
                error_type,
                error_message,
            )
        ):
            raise SubmissionFormatError(
                f"verification row {row_number} skipped fields must be null"
            )
        return

    if not requires_verification:
        raise SubmissionFormatError(
            f"verification row {row_number} requires_verification must be true"
        )

    if status == "verified":
        if not raw_verifier_output:
            raise SubmissionFormatError(
                f"verification row {row_number} raw_verifier_output must be non-empty"
            )
        if after_label is None:
            raise SubmissionFormatError(f"verification row {row_number} after_label is required")
        if verifier_reason is None:
            raise SubmissionFormatError(
                f"verification row {row_number} verifier_reason is required"
            )
        if verifier_evidence_type is None:
            raise SubmissionFormatError(
                f"verification row {row_number} verifier_evidence_type is required"
            )
        if reasoner_defect_found is None or objective_support is None:
            raise SubmissionFormatError(
                f"verification row {row_number} verifier support booleans are required"
            )
        if image_status != "loaded":
            raise SubmissionFormatError(f"verification row {row_number} image_status is invalid")
        if verifier_parse_status != "valid":
            raise SubmissionFormatError(
                f"verification row {row_number} verifier_parse_status is invalid"
            )
        if error_type is not None or error_message is not None:
            raise SubmissionFormatError(
                f"verification row {row_number} verified rows must not include errors"
            )
        if after_label in {"0", "1"} and (
            objective_support is not True
            or verifier_evidence_type not in VALID_SOURCE_SUPPORT_EVIDENCE
        ):
            raise SubmissionFormatError(
                f"verification row {row_number} person after_label requires objective support"
            )
        if after_label == "2" and (
            objective_support is not False or verifier_evidence_type != "insufficient_evidence"
        ):
            raise SubmissionFormatError(
                f"verification row {row_number} label 2 requires insufficient evidence"
            )
        return

    if after_label is not None:
        raise SubmissionFormatError(f"verification row {row_number} after_label must be null")
    if any(
        value is not None
        for value in (
            verifier_reason,
            verifier_evidence_type,
            reasoner_defect_found,
            objective_support,
        )
    ):
        raise SubmissionFormatError(
            f"verification row {row_number} failed verifier fields must be null"
        )
    if image_status is not None and image_status not in VALID_IMAGE_STATUSES:
        raise SubmissionFormatError(f"verification row {row_number} image_status is invalid")
    if (
        verifier_parse_status is not None
        and verifier_parse_status not in VALID_VERIFIER_PARSE_STATUSES
    ):
        raise SubmissionFormatError(
            f"verification row {row_number} verifier_parse_status is invalid"
        )
    if error_type is None or error_message is None:
        raise SubmissionFormatError(
            f"verification row {row_number} error_type and error_message are required"
        )


def _parse_triggers(value: object, row_number: int) -> tuple[VerificationTrigger, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SubmissionFormatError(
            f"verification row {row_number} triggers must be a JSON string array"
        )
    if len(value) != len(set(value)):
        raise SubmissionFormatError(f"verification row {row_number} triggers contains duplicate")
    if any(item not in VALID_TRIGGERS for item in value):
        raise SubmissionFormatError(
            f"verification row {row_number} triggers contains unsupported values"
        )
    ordered = tuple(sorted(value, key=lambda item: TRIGGER_ORDER[item]))
    if tuple(value) != ordered:
        raise SubmissionFormatError(
            f"verification row {row_number} triggers must use deterministic ordering"
        )
    return cast(tuple[VerificationTrigger, ...], tuple(value))


def _required_text(value: object, row_number: int, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SubmissionFormatError(
            f"verification row {row_number} {field_name} must be a non-empty string"
        )
    _require_utf8(value, f"verification row {row_number} {field_name}")
    return value


def _optional_text(value: object, row_number: int, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, row_number, field_name)


def _required_bool(value: object, row_number: int, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise SubmissionFormatError(f"verification row {row_number} {field_name} must be a boolean")
    return value


def _optional_bool(value: object, row_number: int, field_name: str) -> bool | None:
    if value is None:
        return None
    return _required_bool(value, row_number, field_name)


def _optional_label(value: object, row_number: int, field_name: str) -> ReasonerLabel | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in VALID_LABELS:
        raise SubmissionFormatError(
            f"verification row {row_number} {field_name} must be exactly 0, 1, or 2"
        )
    return cast(ReasonerLabel, value)


def _optional_evidence_type(
    value: object,
    row_number: int,
    field_name: str,
) -> EvidenceType | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in EVIDENCE_TYPES:
        raise SubmissionFormatError(f"verification row {row_number} {field_name} is unsupported")
    return cast(EvidenceType, value)


def _optional_image_status(value: object, row_number: int) -> ImageLoadStatus | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in VALID_IMAGE_STATUSES:
        raise SubmissionFormatError(f"verification row {row_number} image_status is invalid")
    return cast(ImageLoadStatus, value)


def _optional_verifier_parse_status(
    value: object,
    row_number: int,
) -> VerifierParseStatus | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in VALID_VERIFIER_PARSE_STATUSES:
        raise SubmissionFormatError(
            f"verification row {row_number} verifier_parse_status is invalid"
        )
    return cast(VerifierParseStatus, value)


def _required_status(value: object, row_number: int) -> VerificationStatus:
    if not isinstance(value, str) or value not in VALID_STATUSES:
        raise SubmissionFormatError(f"verification row {row_number} status is invalid")
    return cast(VerificationStatus, value)


def _required_nonnegative_float(value: object, row_number: int, field_name: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise SubmissionFormatError(f"verification row {row_number} {field_name} must be a number")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise SubmissionFormatError(
            f"verification row {row_number} {field_name} must be non-negative"
        )
    return numeric


def _parse_generation_metadata(value: object, row_number: int) -> ModelGenerationMetadata | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SubmissionFormatError(
            f"verification row {row_number} generation_metadata must be an object or null"
        )
    try:
        return ModelGenerationMetadata(**value)
    except TypeError as exc:
        raise SubmissionFormatError(
            f"verification row {row_number} generation_metadata is invalid: {exc}"
        ) from exc


def _parse_model_load_metadata(value: object, row_number: int) -> ModelLoadMetadata | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SubmissionFormatError(
            f"verification row {row_number} model_load_metadata must be an object or null"
        )
    metadata = dict(value)
    snapshot_path = metadata.get("snapshot_path")
    if isinstance(snapshot_path, str):
        metadata["snapshot_path"] = Path(snapshot_path)
    try:
        return ModelLoadMetadata(**metadata)
    except TypeError as exc:
        raise SubmissionFormatError(
            f"verification row {row_number} model_load_metadata is invalid: {exc}"
        ) from exc


def _require_text(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SubmissionFormatError(f"{field_name} must be a non-empty string")
    _require_utf8(value, field_name)


def _require_utf8(value: str, field_name: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise SubmissionFormatError(f"{field_name} contains invalid Unicode data") from exc
