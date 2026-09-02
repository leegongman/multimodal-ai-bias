"""Generated-output parsing boundary."""

from __future__ import annotations

import csv
import json
import os
import stat
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from multimodal_bias.exceptions import ParseError
from multimodal_bias.prompting.guards import (
    EVIDENCE_TYPES,
    LEGACY_OUTPUT_FIELDS,
    OUTPUT_FIELDS,
    PARSE_MARKER,
    REASONER_OUTPUT_SCHEMA_VERSION,
    REASONER_PROMPT_SCHEMA_MODES,
    VERIFIER_OUTPUT_FIELDS,
    VERIFIER_PARSE_MARKER,
)
from multimodal_bias.schemas import (
    ParsedReasonerRecord,
    ParsedVerifierOutput,
    ReasonerOutput,
    ReasonerParseResult,
    VerifierOutput,
)

PARSED_REASONER_FILENAME = "parsed_reasoner.csv"
PARSED_REASONER_FIELDNAMES = (
    "run_id",
    "sample_id",
    "parsed_label",
    "uncertainty_option_index",
    "evidence_summary",
    "evidence_type",
    "uncertainty_signal",
    "risk_flags",
    "schema_version",
    "parse_status",
    "parse_error",
)
LEGACY_PARSED_REASONER_FIELDNAMES = (
    "run_id",
    "sample_id",
    "parsed_label",
    "evidence_summary",
    "evidence_type",
    "uncertainty_signal",
    "risk_flags",
    "parse_status",
    "parse_error",
)
RAW_REASONER_STATUSES = frozenset(
    {"generated", "image_failed", "prompt_failed", "inference_failed"}
)
VALID_LABELS = frozenset({"0", "1", "2"})
FINAL_MARKER_PREFIX = f"{PARSE_MARKER}:"
VERIFIER_MARKER_PREFIX = f"{VERIFIER_PARSE_MARKER}:"
VALID_PARSE_STATUSES = frozenset(
    {"valid", "source_failed", "missing_marker", "invalid_json", "invalid_schema", "invalid_label"}
)
VALID_REASONER_RISK_FLAGS = frozenset({"invalid_parse", "protected_attribute_risk"})


class _StrictJsonError(ValueError):
    """Internal signal for JSON syntax rejected by the project contract."""


class _DuplicateKeyError(_StrictJsonError):
    """Internal signal for duplicate JSON object keys."""


def _validate_schema_mode(schema_mode: str) -> None:
    if schema_mode not in {"v2", "v3"}:
        raise ParseError("Reasoner schema_mode must be explicitly v2 or v3")


def parse_reasoner_output(
    raw_output: str,
    *,
    run_id: str,
    sample_id: str,
    schema_mode: str = "v3",
) -> ParsedReasonerRecord:
    """Parse one generated Reasoner text without inventing fallback labels."""

    _require_identity(run_id, sample_id)
    _validate_schema_mode(schema_mode)
    if not isinstance(raw_output, str):
        raise ParseError(f"raw output for sample {sample_id} must be a string")

    final_line = next(
        (line for line in reversed(raw_output.splitlines()) if line.strip()),
        None,
    )
    if final_line is None or not final_line.startswith(FINAL_MARKER_PREFIX):
        return _invalid_record(
            run_id,
            sample_id,
            "missing_marker",
            f"sample {sample_id} final non-empty line must start with {FINAL_MARKER_PREFIX}",
        )

    encoded_payload = final_line[len(FINAL_MARKER_PREFIX) :]
    try:
        payload = _loads_unique(encoded_payload)
    except (ValueError, RecursionError) as exc:
        return _invalid_record(
            run_id,
            sample_id,
            "invalid_json",
            f"sample {sample_id} final answer JSON is invalid: {exc}",
        )

    if not isinstance(payload, dict):
        return _invalid_schema_record(sample_id, run_id, "final answer must be a JSON object")

    payload_keys = set(payload)
    required_fields = OUTPUT_FIELDS if schema_mode == "v3" else LEGACY_OUTPUT_FIELDS
    required_keys = set(required_fields)
    if payload_keys != required_keys:
        missing = sorted(required_keys - payload_keys)
        extra = sorted(payload_keys - required_keys)
        details: list[str] = []
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        if extra:
            details.append(f"extra fields: {', '.join(extra)}")
        return _invalid_schema_record(sample_id, run_id, "; ".join(details))

    label = payload["label"]
    if not isinstance(label, str) or label not in VALID_LABELS:
        return _invalid_record(
            run_id,
            sample_id,
            "invalid_label",
            f"sample {sample_id} label must be exactly one of: 0, 1, 2",
        )

    evidence = payload["evidence"]
    if not isinstance(evidence, str) or not evidence.strip() or not _is_utf8_encodable(evidence):
        return _invalid_schema_record(sample_id, run_id, "evidence must be a non-empty string")

    evidence_type = payload["evidence_type"]
    if not isinstance(evidence_type, str) or evidence_type not in EVIDENCE_TYPES:
        return _invalid_schema_record(
            sample_id,
            run_id,
            "evidence_type must be one of: " + ", ".join(EVIDENCE_TYPES),
        )

    uncertainty_signal = payload["uncertainty_signal"]
    if type(uncertainty_signal) is not bool:
        return _invalid_schema_record(
            sample_id,
            run_id,
            "uncertainty_signal must be a JSON boolean",
        )

    protected_attribute_risk = payload["protected_attribute_risk"]
    if type(protected_attribute_risk) is not bool:
        return _invalid_schema_record(
            sample_id,
            run_id,
            "protected_attribute_risk must be a JSON boolean",
        )

    risk_flags = ("protected_attribute_risk",) if protected_attribute_risk else ()
    if schema_mode == "v2":
        return ParsedReasonerRecord(
            run_id=run_id,
            sample_id=sample_id,
            parsed_label=label,
            evidence_summary=evidence,
            evidence_type=evidence_type,
            uncertainty_signal=uncertainty_signal,
            risk_flags=risk_flags,
            parse_status="valid",
            parse_error=None,
        )

    uncertainty_option_index = payload["uncertainty_option_index"]
    if type(uncertainty_option_index) is not int or uncertainty_option_index not in range(3):
        return _invalid_schema_record(
            sample_id,
            run_id,
            "uncertainty_option_index must be a JSON integer from 0 through 2",
        )

    schema_version = payload["schema_version"]
    if schema_version != REASONER_OUTPUT_SCHEMA_VERSION:
        return _invalid_schema_record(
            sample_id,
            run_id,
            f"schema_version must be exactly {REASONER_OUTPUT_SCHEMA_VERSION}",
        )

    selected_uncertainty = label == str(uncertainty_option_index)
    if uncertainty_signal is not selected_uncertainty:
        return _invalid_schema_record(
            sample_id,
            run_id,
            "uncertainty_signal must equal label == uncertainty_option_index",
        )
    if selected_uncertainty and evidence_type != "insufficient_evidence":
        return _invalid_schema_record(
            sample_id, run_id, "uncertainty selection requires insufficient_evidence"
        )
    if not selected_uncertainty and evidence_type == "insufficient_evidence":
        return _invalid_schema_record(
            sample_id, run_id, "decisive selection requires decisive evidence"
        )

    output = ReasonerOutput(
        label=label,
        evidence=evidence,
        evidence_type=evidence_type,
        uncertainty_signal=uncertainty_signal,
        protected_attribute_risk=protected_attribute_risk,
        uncertainty_option_index=uncertainty_option_index,
        schema_version=schema_version,
    )
    risk_flags = ("protected_attribute_risk",) if output.protected_attribute_risk else ()
    return ParsedReasonerRecord(
        run_id=run_id,
        sample_id=sample_id,
        parsed_label=output.label,
        evidence_summary=output.evidence,
        evidence_type=output.evidence_type,
        uncertainty_signal=output.uncertainty_signal,
        risk_flags=risk_flags,
        parse_status="valid",
        parse_error=None,
        uncertainty_option_index=output.uncertainty_option_index,
        schema_version=output.schema_version,
    )


def parse_verifier_output(raw_output: str) -> ParsedVerifierOutput:
    """Parse one generated Verifier response without inventing a label."""

    if not isinstance(raw_output, str):
        raise ParseError("raw Verifier output must be a string")
    if not _is_utf8_encodable(raw_output):
        return _invalid_verifier_output(
            "invalid_schema", "raw Verifier output contains invalid Unicode data"
        )
    final_line = next((line for line in reversed(raw_output.splitlines()) if line.strip()), None)
    if final_line is None or not final_line.startswith(VERIFIER_MARKER_PREFIX):
        return _invalid_verifier_output(
            "missing_marker",
            f"final non-empty line must start with {VERIFIER_MARKER_PREFIX}",
        )

    payload_text = final_line[len(VERIFIER_MARKER_PREFIX) :]
    try:
        payload = _loads_unique(payload_text)
    except (ValueError, RecursionError) as exc:
        return _invalid_verifier_output("invalid_json", f"Verifier JSON is invalid: {exc}")
    if not isinstance(payload, dict):
        return _invalid_verifier_output("invalid_schema", "Verifier answer must be an object")

    payload_keys = set(payload)
    required_keys = set(VERIFIER_OUTPUT_FIELDS)
    if payload_keys != required_keys:
        missing = sorted(required_keys - payload_keys)
        extra = sorted(payload_keys - required_keys)
        detail = []
        if missing:
            detail.append(f"missing fields: {', '.join(missing)}")
        if extra:
            detail.append(f"extra fields: {', '.join(extra)}")
        return _invalid_verifier_output("invalid_schema", "; ".join(detail))

    label = payload["label"]
    if not isinstance(label, str) or label not in VALID_LABELS:
        return _invalid_verifier_output("invalid_label", "label must be exactly 0, 1, or 2")
    reason = payload["reason"]
    if not isinstance(reason, str) or not reason.strip() or not _is_utf8_encodable(reason):
        return _invalid_verifier_output("invalid_schema", "reason must be a non-empty string")
    evidence_type = payload["evidence_type"]
    if not isinstance(evidence_type, str) or evidence_type not in EVIDENCE_TYPES:
        return _invalid_verifier_output(
            "invalid_schema",
            "evidence_type must be one of: " + ", ".join(EVIDENCE_TYPES),
        )
    reasoner_defect_found = payload["reasoner_defect_found"]
    objective_support = payload["objective_support"]
    if type(reasoner_defect_found) is not bool:
        return _invalid_verifier_output(
            "invalid_schema", "reasoner_defect_found must be a JSON boolean"
        )
    if type(objective_support) is not bool:
        return _invalid_verifier_output(
            "invalid_schema", "objective_support must be a JSON boolean"
        )

    if label == "2" and (evidence_type != "insufficient_evidence" or objective_support):
        return _invalid_verifier_output(
            "invalid_schema", "label 2 requires insufficient evidence without objective support"
        )
    if label in {"0", "1"} and (evidence_type == "insufficient_evidence" or not objective_support):
        return _invalid_verifier_output(
            "invalid_schema", "person labels require decisive evidence and objective support"
        )

    return ParsedVerifierOutput(
        output=VerifierOutput(
            label=label,
            reason=reason,
            evidence_type=evidence_type,
            reasoner_defect_found=reasoner_defect_found,
            objective_support=objective_support,
        ),
        parse_status="valid",
        parse_error=None,
    )


def read_parsed_reasoner_artifact(
    parsed_reasoner_path: Path | str,
    *,
    expected_run_id: str,
    expected_sample_ids: Sequence[str],
    schema_mode: str = "v3",
) -> tuple[ParsedReasonerRecord, ...]:
    """Read and validate one immutable parsed Reasoner CSV artifact."""

    path = Path(parsed_reasoner_path)
    if path.name != PARSED_REASONER_FILENAME:
        raise ParseError(f"parsed Reasoner artifact must be named {PARSED_REASONER_FILENAME}")
    expected_ids = _validate_expected_context(expected_run_id, expected_sample_ids)
    assert expected_ids is not None
    _validate_schema_mode(schema_mode)
    fieldnames = (
        PARSED_REASONER_FIELDNAMES if schema_mode == "v3" else LEGACY_PARSED_REASONER_FIELDNAMES
    )
    rows = _read_exact_parsed_csv(path, fieldnames)

    records: list[ParsedReasonerRecord] = []
    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        run_id = row["run_id"]
        sample_id = row["sample_id"]
        _require_identity(run_id, sample_id)
        if run_id != expected_run_id:
            raise ParseError(
                f"parsed Reasoner row {row_number} run_id {run_id!r} does not match "
                f"expected run_id {expected_run_id!r}"
            )
        if sample_id in seen:
            raise ParseError(f"parsed Reasoner artifact has duplicate sample_id: {sample_id}")
        seen.add(sample_id)

        parse_status = row["parse_status"]
        if parse_status not in VALID_PARSE_STATUSES:
            raise ParseError(f"parsed Reasoner row {row_number} has invalid parse_status")
        risk_flags = _parse_reasoner_risk_flags(row["risk_flags"], row_number)
        if parse_status != "valid" and "invalid_parse" not in risk_flags:
            raise ParseError(
                f"parsed Reasoner row {row_number} non-valid state requires invalid_parse"
            )
        if parse_status == "valid" and "invalid_parse" in risk_flags:
            raise ParseError(
                f"parsed Reasoner row {row_number} valid state must not carry invalid_parse"
            )
        invalid = parse_status != "valid" or "invalid_parse" in risk_flags
        if invalid:
            parse_error = row["parse_error"]
            if not parse_error.strip() or not _is_utf8_encodable(parse_error):
                raise ParseError(
                    f"parsed Reasoner row {row_number} non-valid state requires parse_error"
                )
            if any(
                row[field]
                for field in (
                    "parsed_label",
                    "evidence_summary",
                    "evidence_type",
                    "uncertainty_signal",
                )
                + (("uncertainty_option_index", "schema_version") if schema_mode == "v3" else ())
            ):
                raise ParseError(
                    f"parsed Reasoner row {row_number} invalid state must not carry valid fields"
                )
            records.append(
                ParsedReasonerRecord(
                    run_id=run_id,
                    sample_id=sample_id,
                    parsed_label=None,
                    evidence_summary=None,
                    evidence_type=None,
                    uncertainty_signal=None,
                    risk_flags=risk_flags,
                    parse_status=parse_status,  # type: ignore[arg-type]
                    parse_error=parse_error,
                )
            )
            continue

        label = row["parsed_label"]
        evidence = row["evidence_summary"]
        evidence_type = row["evidence_type"]
        uncertainty_text = row["uncertainty_signal"]
        uncertainty_index_text = row.get("uncertainty_option_index", "")
        schema_version = row.get("schema_version", "")
        if label not in VALID_LABELS:
            raise ParseError(f"parsed Reasoner row {row_number} has invalid parsed_label")
        if not evidence.strip() or not _is_utf8_encodable(evidence):
            raise ParseError(f"parsed Reasoner row {row_number} has invalid evidence_summary")
        if evidence_type not in EVIDENCE_TYPES:
            raise ParseError(f"parsed Reasoner row {row_number} has invalid evidence_type")
        if uncertainty_text not in {"true", "false"}:
            raise ParseError(f"parsed Reasoner row {row_number} has invalid uncertainty_signal")
        if schema_mode == "v3" and uncertainty_index_text not in {"0", "1", "2"}:
            raise ParseError(
                f"parsed Reasoner row {row_number} has invalid uncertainty_option_index"
            )
        if schema_mode == "v3" and schema_version != REASONER_OUTPUT_SCHEMA_VERSION:
            raise ParseError(f"parsed Reasoner row {row_number} has invalid schema_version")
        uncertainty_index = int(uncertainty_index_text) if schema_mode == "v3" else None
        selected_uncertainty = label == uncertainty_index_text
        if schema_mode == "v3" and (uncertainty_text == "true") is not selected_uncertainty:
            raise ParseError(f"parsed Reasoner row {row_number} has inconsistent uncertainty")
        if (
            schema_mode == "v3"
            and selected_uncertainty
            and evidence_type != "insufficient_evidence"
        ):
            raise ParseError(f"parsed Reasoner row {row_number} has inconsistent evidence_type")
        if (
            schema_mode == "v3"
            and not selected_uncertainty
            and evidence_type == "insufficient_evidence"
        ):
            raise ParseError(f"parsed Reasoner row {row_number} has inconsistent evidence_type")
        if row["parse_error"]:
            raise ParseError(f"parsed Reasoner row {row_number} valid state has parse_error")
        records.append(
            ParsedReasonerRecord(
                run_id=run_id,
                sample_id=sample_id,
                parsed_label=label,  # type: ignore[arg-type]
                evidence_summary=evidence,
                evidence_type=evidence_type,  # type: ignore[arg-type]
                uncertainty_signal=uncertainty_text == "true",
                risk_flags=risk_flags,
                parse_status="valid",
                parse_error=None,
                uncertainty_option_index=uncertainty_index,
                schema_version=schema_version or None,
            )
        )

    actual_ids = tuple(record.sample_id for record in records)
    if actual_ids != expected_ids:
        raise ParseError(
            "parsed Reasoner ordered sample IDs do not match expected inference set: "
            f"expected_count={len(expected_ids)} actual_count={len(actual_ids)}"
        )
    return tuple(records)


def parse_reasoner_artifact(
    raw_reasoner_path: Path | str,
    parsed_reasoner_path: Path | str | None = None,
    *,
    expected_run_id: str | None = None,
    expected_sample_ids: Sequence[str] | None = None,
    schema_mode: str = "v3",
) -> ReasonerParseResult:
    """Parse one immutable raw Reasoner JSONL artifact into an atomic CSV artifact."""

    raw_path = Path(raw_reasoner_path)
    output_path = (
        Path(parsed_reasoner_path)
        if parsed_reasoner_path is not None
        else raw_path.parent / PARSED_REASONER_FILENAME
    )
    expected_ids = _validate_expected_context(expected_run_id, expected_sample_ids)
    _validate_artifact_paths(raw_path, output_path)
    _validate_schema_mode(schema_mode)
    fieldnames = (
        PARSED_REASONER_FIELDNAMES if schema_mode == "v3" else LEGACY_PARSED_REASONER_FIELDNAMES
    )
    records = _read_raw_records(
        raw_path,
        expected_run_id=expected_run_id,
        expected_sample_ids=expected_ids,
        schema_mode=schema_mode,
    )

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as csv_file:
            temp_path = Path(csv_file.name)
            writer = csv.DictWriter(
                csv_file,
                fieldnames=list(fieldnames),
                lineterminator="\n",
            )
            writer.writeheader()
            for record in records:
                _write_csv_record(writer, record, schema_mode=schema_mode)
        try:
            os.link(temp_path, output_path)
        except FileExistsError as exc:
            raise ParseError(f"parsed Reasoner artifact already exists: {output_path}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    valid_count = sum(record.parse_status == "valid" for record in records)
    return ReasonerParseResult(
        parsed_reasoner_path=output_path,
        records=records,
        total_samples=len(records),
        valid_count=valid_count,
        invalid_count=len(records) - valid_count,
    )


def _validate_artifact_paths(raw_path: Path, output_path: Path) -> None:
    try:
        if not raw_path.is_file():
            raise ParseError(f"raw Reasoner artifact does not exist: {raw_path}")
        if output_path.name != PARSED_REASONER_FILENAME:
            raise ParseError(
                f"parsed Reasoner artifact must be named {PARSED_REASONER_FILENAME}: {output_path}"
            )
        if output_path.parent.resolve() != raw_path.parent.resolve():
            raise ParseError("parsed Reasoner artifact must be written beside raw_reasoner.jsonl")
        if output_path.exists():
            raise ParseError(f"parsed Reasoner artifact already exists: {output_path}")
    except OSError as exc:
        raise ParseError(f"Reasoner artifact path could not be validated: {exc}") from exc


def _read_raw_records(
    raw_path: Path,
    *,
    expected_run_id: str | None,
    expected_sample_ids: tuple[str, ...] | None,
    schema_mode: str,
) -> tuple[ParsedReasonerRecord, ...]:
    try:
        lines = raw_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ParseError(f"raw Reasoner artifact is not valid UTF-8: {raw_path}: {exc}") from exc
    except OSError as exc:
        raise ParseError(f"raw Reasoner artifact could not be read: {raw_path}: {exc}") from exc

    if not lines:
        raise ParseError(f"raw Reasoner artifact is empty: {raw_path}")

    records: list[ParsedReasonerRecord] = []
    seen_sample_ids: set[str] = set()
    observed_run_id: str | None = None
    observed_prompt_version: str | None = None
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise ParseError(f"raw Reasoner artifact contains blank line {line_number}: {raw_path}")
        try:
            raw_record = _loads_unique(line)
        except (ValueError, RecursionError) as exc:
            raise ParseError(
                f"raw Reasoner JSONL line {line_number} is invalid: {raw_path}: {exc}"
            ) from exc
        if not isinstance(raw_record, dict):
            raise ParseError(f"raw Reasoner JSONL line {line_number} must be a JSON object")

        run_id = raw_record.get("run_id")
        sample_id = raw_record.get("sample_id")
        if not isinstance(run_id, str) or not run_id.strip():
            raise ParseError(f"raw Reasoner JSONL line {line_number} has invalid run_id")
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ParseError(f"raw Reasoner JSONL line {line_number} has invalid sample_id")
        _require_utf8_text(run_id, f"raw Reasoner JSONL line {line_number} run_id")
        _require_utf8_text(sample_id, f"raw Reasoner JSONL line {line_number} sample_id")
        prompt_version = raw_record.get("prompt_version")
        if (
            not isinstance(prompt_version, str)
            or prompt_version not in REASONER_PROMPT_SCHEMA_MODES
        ):
            raise ParseError(f"raw Reasoner JSONL line {line_number} has invalid prompt_version")
        if REASONER_PROMPT_SCHEMA_MODES[prompt_version] != schema_mode:
            raise ParseError(
                f"raw Reasoner prompt_version {prompt_version!r} does not match "
                f"schema_mode {schema_mode!r}"
            )
        if observed_prompt_version is None:
            observed_prompt_version = prompt_version
        elif prompt_version != observed_prompt_version:
            raise ParseError(
                "raw Reasoner artifact mixes prompt_version values: "
                f"{observed_prompt_version} and {prompt_version}"
            )
        if expected_run_id is not None and run_id != expected_run_id:
            raise ParseError(
                f"raw Reasoner run_id {run_id!r} does not match expected run_id {expected_run_id!r}"
            )
        if observed_run_id is None:
            observed_run_id = run_id
        elif run_id != observed_run_id:
            raise ParseError(
                f"raw Reasoner artifact mixes run_id values: {observed_run_id} and {run_id}"
            )
        if sample_id in seen_sample_ids:
            raise ParseError(f"raw Reasoner artifact has duplicate sample_id: {sample_id}")
        seen_sample_ids.add(sample_id)

        status = raw_record.get("status")
        raw_output = raw_record.get("raw_output")
        if not isinstance(status, str) or status not in RAW_REASONER_STATUSES:
            raise ParseError(
                f"raw Reasoner JSONL line {line_number} has invalid status: {status!r}"
            )
        if status == "generated":
            if not isinstance(raw_output, str):
                records.append(
                    _invalid_record(
                        run_id,
                        sample_id,
                        "source_failed",
                        f"sample {sample_id} generated row is missing string raw_output",
                    )
                )
                continue
            records.append(
                parse_reasoner_output(
                    raw_output,
                    run_id=run_id,
                    sample_id=sample_id,
                    schema_mode=schema_mode,
                )
            )
            continue
        if raw_output is not None:
            raise ParseError(f"raw Reasoner failure row {sample_id} must contain null raw_output")
        records.append(_source_failure_record(raw_record, run_id, sample_id, status))

    parsed_records = tuple(records)
    if expected_sample_ids is not None:
        actual_sample_ids = tuple(record.sample_id for record in parsed_records)
        if actual_sample_ids != expected_sample_ids:
            raise ParseError(
                "raw Reasoner ordered sample IDs do not match expected inference set: "
                f"expected_count={len(expected_sample_ids)} actual_count={len(actual_sample_ids)}"
            )

    return parsed_records


def _source_failure_record(
    raw_record: dict[str, Any],
    run_id: str,
    sample_id: str,
    status: str,
) -> ParsedReasonerRecord:
    error_type = raw_record.get("error_type")
    error_message = raw_record.get("error_message")
    details = ": ".join(
        str(value).strip()
        for value in (error_type, error_message)
        if isinstance(value, str) and value.strip()
    )
    suffix = f": {details}" if details else ""
    return _invalid_record(
        run_id,
        sample_id,
        "source_failed",
        f"sample {sample_id} raw Reasoner status is {status}{suffix}",
    )


def _invalid_schema_record(
    sample_id: str,
    run_id: str,
    detail: str,
) -> ParsedReasonerRecord:
    return _invalid_record(
        run_id,
        sample_id,
        "invalid_schema",
        f"sample {sample_id} final answer schema is invalid: {detail}",
    )


def _invalid_record(
    run_id: str,
    sample_id: str,
    parse_status: str,
    parse_error: str,
) -> ParsedReasonerRecord:
    return ParsedReasonerRecord(
        run_id=run_id,
        sample_id=sample_id,
        parsed_label=None,
        evidence_summary=None,
        evidence_type=None,
        uncertainty_signal=None,
        risk_flags=("invalid_parse",),
        parse_status=parse_status,
        parse_error=_safe_utf8_text(parse_error),
    )


def _write_csv_record(
    writer: csv.DictWriter,
    record: ParsedReasonerRecord,
    *,
    schema_mode: str,
) -> None:
    row = {
        "run_id": record.run_id,
        "sample_id": record.sample_id,
        "parsed_label": record.parsed_label or "",
        "uncertainty_option_index": (
            "" if record.uncertainty_option_index is None else str(record.uncertainty_option_index)
        ),
        "evidence_summary": record.evidence_summary or "",
        "evidence_type": record.evidence_type or "",
        "uncertainty_signal": (
            "" if record.uncertainty_signal is None else str(record.uncertainty_signal).lower()
        ),
        "risk_flags": json.dumps(
            list(record.risk_flags),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "schema_version": record.schema_version or "",
        "parse_status": record.parse_status,
        "parse_error": record.parse_error or "",
    }
    if schema_mode == "v2":
        row.pop("uncertainty_option_index")
        row.pop("schema_version")
    writer.writerow(row)


def _invalid_verifier_output(status: str, detail: str) -> ParsedVerifierOutput:
    return ParsedVerifierOutput(
        output=None,
        parse_status=status,  # type: ignore[arg-type]
        parse_error=_safe_utf8_text(detail),
    )


def _read_exact_parsed_csv(path: Path, fieldnames: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    try:
        with _open_utf8_csv_no_follow(path) as csv_file:
            reader = csv.reader(csv_file, strict=True)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ParseError(f"parsed Reasoner artifact is empty: {path}") from exc
            if tuple(header) != fieldnames:
                raise ParseError(
                    "parsed Reasoner headers must be exactly: " + ", ".join(fieldnames)
                )
            rows: list[dict[str, str]] = []
            for row_number, values in enumerate(reader, start=2):
                if not values:
                    raise ParseError(f"parsed Reasoner artifact contains blank row {row_number}")
                if len(values) != len(fieldnames):
                    raise ParseError(
                        f"parsed Reasoner row {row_number} has {len(values)} fields; "
                        f"expected {len(fieldnames)}"
                    )
                rows.append(dict(zip(fieldnames, values, strict=True)))
    except ParseError:
        raise
    except UnicodeDecodeError as exc:
        raise ParseError(f"parsed Reasoner artifact is not valid UTF-8: {path}: {exc}") from exc
    except csv.Error as exc:
        raise ParseError(f"parsed Reasoner artifact is malformed CSV: {path}: {exc}") from exc
    except OSError as exc:
        raise ParseError(f"parsed Reasoner artifact could not be read: {path}: {exc}") from exc
    if not rows:
        raise ParseError(f"parsed Reasoner artifact has no data rows: {path}")
    return tuple(rows)


def _open_utf8_csv_no_follow(path: Path):
    file_descriptor: int | None = None
    try:
        link_stat = path.lstat()
        if stat.S_ISLNK(link_stat.st_mode):
            raise ParseError(f"parsed Reasoner artifact must not be a symlink: {path}")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        file_descriptor = os.open(path, flags)
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ParseError(f"parsed Reasoner artifact must be a regular file: {path}")
        csv_file = open(file_descriptor, encoding="utf-8", newline="", closefd=True)
        file_descriptor = None
        return csv_file
    except ParseError:
        raise
    except OSError as exc:
        raise ParseError(f"parsed Reasoner artifact could not be read: {path}: {exc}") from exc
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)


def _parse_reasoner_risk_flags(raw_value: str, row_number: int) -> tuple[str, ...]:
    try:
        parsed = _loads_unique(raw_value)
    except (ValueError, RecursionError) as exc:
        raise ParseError(
            f"parsed Reasoner row {row_number} risk_flags is invalid JSON: {exc}"
        ) from exc
    if not isinstance(parsed, list) or any(
        not isinstance(flag, str) or flag not in VALID_REASONER_RISK_FLAGS for flag in parsed
    ):
        raise ParseError(f"parsed Reasoner row {row_number} has invalid risk_flags")
    if len(set(parsed)) != len(parsed):
        raise ParseError(f"parsed Reasoner row {row_number} has duplicate risk_flags")
    deterministic = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
    if raw_value != deterministic:
        raise ParseError(
            f"parsed Reasoner row {row_number} risk_flags must use deterministic JSON encoding"
        )
    return tuple(parsed)


def _loads_unique(value: str) -> object:
    return json.loads(
        value,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_non_standard_constant,
    )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate key: {key!r}")
        result[key] = value
    return result


def _reject_non_standard_constant(value: str) -> object:
    raise _StrictJsonError(f"non-standard JSON constant: {value}")


def _require_identity(run_id: str, sample_id: str) -> None:
    if not isinstance(run_id, str) or not run_id.strip():
        raise ParseError("run_id must be a non-empty string")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ParseError("sample_id must be a non-empty string")
    _require_utf8_text(run_id, "run_id")
    _require_utf8_text(sample_id, "sample_id")


def _validate_expected_context(
    expected_run_id: str | None,
    expected_sample_ids: Sequence[str] | None,
) -> tuple[str, ...] | None:
    if expected_run_id is not None:
        if not isinstance(expected_run_id, str) or not expected_run_id.strip():
            raise ParseError("expected run_id must be a non-empty string")
        _require_utf8_text(expected_run_id, "expected run_id")

    if expected_sample_ids is None:
        return None
    if isinstance(expected_sample_ids, str):
        raise ParseError("expected sample IDs must be a sequence of strings")

    normalized = tuple(expected_sample_ids)
    seen: set[str] = set()
    for index, sample_id in enumerate(normalized):
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ParseError(f"expected sample ID at index {index} must be a non-empty string")
        _require_utf8_text(sample_id, f"expected sample ID at index {index}")
        if sample_id in seen:
            raise ParseError(f"expected sample IDs contain duplicate value: {sample_id}")
        seen.add(sample_id)
    return normalized


def _require_utf8_text(value: str, field_name: str) -> None:
    if not _is_utf8_encodable(value):
        raise ParseError(f"{field_name} contains invalid Unicode surrogate data")


def _is_utf8_encodable(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _safe_utf8_text(value: str) -> str:
    return value.encode("utf-8", errors="backslashreplace").decode("utf-8")
