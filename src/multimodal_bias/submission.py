"""Validated final-prediction and Multimodal submission artifact boundary."""

from __future__ import annotations

import csv
import json
import os
import stat
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from multimodal_bias.exceptions import SubmissionFormatError
from multimodal_bias.parsing import PARSED_REASONER_FIELDNAMES
from multimodal_bias.prompting.guards import EVIDENCE_TYPES, REASONER_OUTPUT_SCHEMA_VERSION
from multimodal_bias.schemas import (
    FinalPrediction,
    FinalSourceStage,
    ReasonerLabel,
    SubmissionResult,
)

FINAL_PREDICTIONS_FILENAME = "final_predictions.csv"
SUBMISSION_FILENAME = "submission.csv"
FINAL_PREDICTIONS_FIELDNAMES = (
    "run_id",
    "sample_id",
    "final_label",
    "source_stage",
    "decision_reason",
)
SUBMISSION_FIELDNAMES = ("sample_id", "label")

VALID_LABELS = frozenset({"0", "1", "2"})
VALID_SOURCE_STAGES = frozenset({"reasoner", "verifier", "arbitration"})
VALID_REASONER_RISK_FLAGS = frozenset({"protected_attribute_risk"})
REASONER_SOURCE_STAGE: FinalSourceStage = "reasoner"
REASONER_DECISION_REASON = "validated_reasoner_output"
FileIdentity = tuple[int, int]


def resolve_run_directory(runs_root: Path | str, run_id: str) -> Path:
    """Resolve one non-symlink run directory beneath the configured runs root."""

    _validate_run_id_value(run_id, "run_id")

    try:
        root = Path(runs_root)
        if not root.is_dir():
            raise SubmissionFormatError(f"configured runs root does not exist: {root}")
        resolved_root = root.resolve(strict=True)
        candidate = root / run_id
        if candidate.is_symlink():
            raise SubmissionFormatError(f"run directory must not be a symlink: {candidate}")
        if not candidate.is_dir():
            raise SubmissionFormatError(f"run directory does not exist: {candidate}")
        resolved_candidate = candidate.resolve(strict=True)
        if resolved_candidate.parent != resolved_root or resolved_candidate.name != run_id:
            raise SubmissionFormatError("run_id resolves outside the configured runs root")
    except SubmissionFormatError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise SubmissionFormatError(f"run_id path could not be resolved: {exc}") from exc
    return resolved_candidate


def generate_submission_artifacts(
    parsed_reasoner_path: Path | str,
    run_dir: Path | str,
    *,
    expected_run_id: str,
    expected_sample_ids: Sequence[str],
    final_predictions_path: Path | str | None = None,
    submission_path: Path | str | None = None,
) -> SubmissionResult:
    """Validate one parsed run and publish an immutable final/submission pair."""

    run_path, parsed_path, final_path, multimodal_path, expected_ids = _validate_paths_and_context(
        parsed_reasoner_path,
        run_dir,
        expected_run_id=expected_run_id,
        expected_sample_ids=expected_sample_ids,
        final_predictions_path=final_predictions_path,
        submission_path=submission_path,
    )
    parsed_rows = _read_parsed_reasoner(
        parsed_path,
        expected_run_id=expected_run_id,
        expected_sample_ids=expected_ids,
    )
    predictions = tuple(
        FinalPrediction(
            run_id=row["run_id"],
            sample_id=row["sample_id"],
            final_label=cast(ReasonerLabel, row["parsed_label"]),
            source_stage=REASONER_SOURCE_STAGE,
            decision_reason=REASONER_DECISION_REASON,
        )
        for row in parsed_rows
    )

    return _publish_validated_predictions(
        run_path,
        final_path,
        multimodal_path,
        predictions,
        expected_run_id=expected_run_id,
        expected_sample_ids=expected_ids,
    )


def generate_submission_artifacts_from_predictions(
    predictions: Sequence[FinalPrediction],
    run_dir: Path | str,
    *,
    expected_run_id: str,
    expected_sample_ids: Sequence[str],
    final_predictions_path: Path | str | None = None,
    submission_path: Path | str | None = None,
) -> SubmissionResult:
    """Publish validated final predictions and the Multimodal submission CSV."""

    run_path, final_path, multimodal_path, expected_ids = _validate_prediction_context(
        run_dir,
        expected_run_id=expected_run_id,
        expected_sample_ids=expected_sample_ids,
        final_predictions_path=final_predictions_path,
        submission_path=submission_path,
    )
    validated_predictions = _validate_prediction_contracts(
        predictions,
        expected_run_id=expected_run_id,
        expected_sample_ids=expected_ids,
    )
    return _publish_validated_predictions(
        run_path,
        final_path,
        multimodal_path,
        validated_predictions,
        expected_run_id=expected_run_id,
        expected_sample_ids=expected_ids,
    )


def _publish_validated_predictions(
    run_path: Path,
    final_path: Path,
    multimodal_path: Path,
    predictions: tuple[FinalPrediction, ...],
    *,
    expected_run_id: str,
    expected_sample_ids: tuple[str, ...],
) -> SubmissionResult:
    final_temp: Path | None = None
    submission_temp: Path | None = None
    try:
        final_temp = _write_final_predictions_temp(run_path, predictions)
        final_identity = _regular_file_identity(final_temp, "staged final predictions artifact")
        validated_predictions = _read_final_predictions(
            final_temp,
            expected_run_id=expected_run_id,
            expected_sample_ids=expected_sample_ids,
        )
        if (
            _regular_file_identity(final_temp, "staged final predictions artifact")
            != final_identity
        ):
            raise SubmissionFormatError(
                "staged final predictions artifact changed during validation"
            )
        if validated_predictions != predictions:
            raise SubmissionFormatError(
                "staged final predictions artifact does not match validated parsed predictions"
            )
        submission_temp = _write_submission_temp(run_path, validated_predictions)
        submission_identity = _regular_file_identity(
            submission_temp,
            "staged Multimodal submission artifact",
        )
        _read_submission(
            submission_temp,
            expected_predictions=validated_predictions,
        )
        if (
            _regular_file_identity(submission_temp, "staged Multimodal submission artifact")
            != submission_identity
        ):
            raise SubmissionFormatError(
                "staged Multimodal submission artifact changed during validation"
            )
        _publish_artifact_pair(
            final_temp,
            final_path,
            submission_temp,
            multimodal_path,
            final_identity=final_identity,
            submission_identity=submission_identity,
        )
    finally:
        if final_temp is not None:
            _cleanup_temp_file(final_temp)
        if submission_temp is not None:
            _cleanup_temp_file(submission_temp)

    return SubmissionResult(
        final_predictions_path=final_path,
        submission_path=multimodal_path,
        predictions=validated_predictions,
        total_samples=len(validated_predictions),
    )


def _validate_prediction_context(
    run_dir: Path | str,
    *,
    expected_run_id: str,
    expected_sample_ids: Sequence[str],
    final_predictions_path: Path | str | None,
    submission_path: Path | str | None,
) -> tuple[Path, Path, Path, tuple[str, ...]]:
    _validate_run_id_value(expected_run_id, "expected run_id")
    expected_ids = _validate_expected_sample_ids(expected_sample_ids)

    try:
        run_path = Path(run_dir)
        if run_path.is_symlink():
            raise SubmissionFormatError(f"run directory must not be a symlink: {run_path}")
        if not run_path.is_dir():
            raise SubmissionFormatError(f"run directory does not exist: {run_path}")
        resolved_run = run_path.resolve(strict=True)
        if resolved_run.name != expected_run_id:
            raise SubmissionFormatError(
                f"run directory name does not match expected run_id: "
                f"{resolved_run.name!r} != {expected_run_id!r}"
            )

        final_path = _canonical_output_path(
            final_predictions_path,
            run_path,
            resolved_run,
            FINAL_PREDICTIONS_FILENAME,
        )
        multimodal_path = _canonical_output_path(
            submission_path,
            run_path,
            resolved_run,
            SUBMISSION_FILENAME,
        )
        for output_path in (final_path, multimodal_path):
            if output_path.exists() or output_path.is_symlink():
                raise SubmissionFormatError(f"submission artifact already exists: {output_path}")
    except SubmissionFormatError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise SubmissionFormatError(f"submission artifact path is invalid: {exc}") from exc

    return run_path, final_path, multimodal_path, expected_ids


def _validate_paths_and_context(
    parsed_reasoner_path: Path | str,
    run_dir: Path | str,
    *,
    expected_run_id: str,
    expected_sample_ids: Sequence[str],
    final_predictions_path: Path | str | None,
    submission_path: Path | str | None,
) -> tuple[Path, Path, Path, Path, tuple[str, ...]]:
    _validate_run_id_value(expected_run_id, "expected run_id")
    expected_ids = _validate_expected_sample_ids(expected_sample_ids)

    try:
        run_path = Path(run_dir)
        if run_path.is_symlink():
            raise SubmissionFormatError(f"run directory must not be a symlink: {run_path}")
        if not run_path.is_dir():
            raise SubmissionFormatError(f"run directory does not exist: {run_path}")
        resolved_run = run_path.resolve(strict=True)
        if resolved_run.name != expected_run_id:
            raise SubmissionFormatError(
                f"run directory name does not match expected run_id: "
                f"{resolved_run.name!r} != {expected_run_id!r}"
            )

        parsed_path = Path(parsed_reasoner_path)
        if parsed_path.name != "parsed_reasoner.csv":
            raise SubmissionFormatError("parsed Reasoner artifact must use its canonical filename")
        if parsed_path.is_symlink() or parsed_path.parent.resolve(strict=True) != resolved_run:
            raise SubmissionFormatError(
                "parsed Reasoner artifact must be directly inside the selected run directory"
            )
        if not parsed_path.is_file():
            raise SubmissionFormatError(f"parsed Reasoner artifact does not exist: {parsed_path}")

        final_path = _canonical_output_path(
            final_predictions_path,
            run_path,
            resolved_run,
            FINAL_PREDICTIONS_FILENAME,
        )
        multimodal_path = _canonical_output_path(
            submission_path,
            run_path,
            resolved_run,
            SUBMISSION_FILENAME,
        )
        for output_path in (final_path, multimodal_path):
            if output_path.exists() or output_path.is_symlink():
                raise SubmissionFormatError(f"submission artifact already exists: {output_path}")
    except SubmissionFormatError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise SubmissionFormatError(f"submission artifact path is invalid: {exc}") from exc

    return run_path, parsed_path, final_path, multimodal_path, expected_ids


def _validate_expected_sample_ids(expected_sample_ids: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(expected_sample_ids, Sequence) or isinstance(expected_sample_ids, str):
        raise SubmissionFormatError("expected sample IDs must be a sequence of strings")

    expected_ids = tuple(expected_sample_ids)
    seen: set[str] = set()
    for index, sample_id in enumerate(expected_ids):
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise SubmissionFormatError(
                f"expected sample ID at index {index} must be a non-empty string"
            )
        _require_utf8(sample_id, f"expected sample ID at index {index}")
        if sample_id in seen:
            raise SubmissionFormatError(f"expected sample IDs contain duplicate value: {sample_id}")
        seen.add(sample_id)
    if not expected_ids:
        raise SubmissionFormatError("expected sample IDs must not be empty")
    return expected_ids


def _validate_prediction_contracts(
    predictions: Sequence[FinalPrediction],
    *,
    expected_run_id: str,
    expected_sample_ids: tuple[str, ...],
) -> tuple[FinalPrediction, ...]:
    if not isinstance(predictions, Sequence) or isinstance(predictions, (str, bytes)):
        raise SubmissionFormatError("final predictions must be a sequence")
    validated: list[FinalPrediction] = []
    seen: set[str] = set()
    for index, prediction in enumerate(predictions):
        if not isinstance(prediction, FinalPrediction):
            raise SubmissionFormatError(f"final prediction at index {index} has invalid type")
        if prediction.run_id != expected_run_id:
            raise SubmissionFormatError(
                f"final prediction at index {index} run_id does not match expected run_id"
            )
        if not isinstance(prediction.sample_id, str) or not prediction.sample_id.strip():
            raise SubmissionFormatError(f"final prediction at index {index} sample_id is invalid")
        _require_utf8(prediction.sample_id, f"final prediction at index {index} sample_id")
        if prediction.sample_id in seen:
            raise SubmissionFormatError(
                f"final predictions contain duplicate sample_id: {prediction.sample_id}"
            )
        seen.add(prediction.sample_id)
        if prediction.final_label not in VALID_LABELS:
            raise SubmissionFormatError(
                f"final prediction at index {index} final_label must be exactly 0, 1, or 2"
            )
        if prediction.source_stage not in VALID_SOURCE_STAGES:
            raise SubmissionFormatError(
                f"final prediction at index {index} source_stage is invalid"
            )
        if (
            not isinstance(prediction.decision_reason, str)
            or not prediction.decision_reason.strip()
            or prediction.decision_reason != prediction.decision_reason.strip()
        ):
            raise SubmissionFormatError(
                f"final prediction at index {index} decision_reason must be non-empty"
            )
        _require_utf8(
            prediction.decision_reason,
            f"final prediction at index {index} decision_reason",
        )
        validated.append(prediction)

    actual_ids = tuple(prediction.sample_id for prediction in validated)
    if actual_ids != expected_sample_ids:
        raise SubmissionFormatError(
            "final predictions ordered sample IDs do not match the official test set"
        )
    return tuple(validated)


def _canonical_output_path(
    requested_path: Path | str | None,
    run_path: Path,
    resolved_run: Path,
    filename: str,
) -> Path:
    output_path = Path(requested_path) if requested_path is not None else run_path / filename
    if output_path.name != filename or output_path.parent.resolve(strict=True) != resolved_run:
        raise SubmissionFormatError(
            f"{filename} must use its canonical filename directly inside the selected run directory"
        )
    return output_path


def _read_parsed_reasoner(
    parsed_path: Path,
    *,
    expected_run_id: str,
    expected_sample_ids: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
    rows = _read_exact_csv(
        parsed_path,
        expected_fieldnames=PARSED_REASONER_FIELDNAMES,
        artifact_name="parsed Reasoner artifact",
    )
    seen: set[str] = set()
    validated: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=2):
        run_id = row["run_id"]
        sample_id = row["sample_id"]
        if run_id != expected_run_id:
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} run_id does not match expected run_id"
            )
        if not sample_id.strip():
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} sample_id must be non-empty"
            )
        _require_utf8(sample_id, f"parsed Reasoner row {row_number} sample_id")
        if sample_id in seen:
            raise SubmissionFormatError(
                f"parsed Reasoner artifact has duplicate sample_id: {sample_id}"
            )
        seen.add(sample_id)

        label = row["parsed_label"]
        if label not in VALID_LABELS:
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} parsed_label must be exactly 0, 1, or 2"
            )
        evidence = row["evidence_summary"]
        if not evidence.strip():
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} evidence_summary must be non-empty"
            )
        _require_utf8(evidence, f"parsed Reasoner row {row_number} evidence_summary")
        if row["evidence_type"] not in EVIDENCE_TYPES:
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} evidence_type is unsupported"
            )
        if row["uncertainty_signal"] not in {"true", "false"}:
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} uncertainty_signal must be true or false"
            )
        uncertainty_index = row["uncertainty_option_index"]
        if uncertainty_index not in VALID_LABELS:
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} uncertainty_option_index must be 0, 1, or 2"
            )
        if row["schema_version"] != REASONER_OUTPUT_SCHEMA_VERSION:
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} schema_version must be "
                f"{REASONER_OUTPUT_SCHEMA_VERSION}"
            )
        selected_uncertainty = label == uncertainty_index
        if (row["uncertainty_signal"] == "true") is not selected_uncertainty:
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} uncertainty fields are inconsistent"
            )
        if selected_uncertainty and row["evidence_type"] != "insufficient_evidence":
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} uncertainty evidence is inconsistent"
            )
        if not selected_uncertainty and row["evidence_type"] == "insufficient_evidence":
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} decisive evidence is inconsistent"
            )
        _validate_risk_flags(row["risk_flags"], row_number)
        if row["parse_status"] != "valid":
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} parse_status must be valid"
            )
        if row["parse_error"] != "":
            raise SubmissionFormatError(
                f"parsed Reasoner row {row_number} parse_error must be empty for a valid row"
            )
        validated.append(row)

    actual_ids = tuple(row["sample_id"] for row in validated)
    if actual_ids != expected_sample_ids:
        raise SubmissionFormatError(
            "parsed Reasoner ordered sample IDs do not match the official test set: "
            f"expected_count={len(expected_sample_ids)} actual_count={len(actual_ids)}"
        )
    return tuple(validated)


def _validate_risk_flags(raw_flags: str, row_number: int) -> None:
    try:
        flags = json.loads(raw_flags)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise SubmissionFormatError(
            f"parsed Reasoner row {row_number} risk_flags is invalid JSON: {exc}"
        ) from exc
    if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
        raise SubmissionFormatError(
            f"parsed Reasoner row {row_number} risk_flags must be a JSON string array"
        )
    if len(flags) != len(set(flags)) or any(
        flag not in VALID_REASONER_RISK_FLAGS for flag in flags
    ):
        raise SubmissionFormatError(
            f"parsed Reasoner row {row_number} risk_flags contains unsupported values"
        )
    deterministic = json.dumps(flags, ensure_ascii=False, separators=(",", ":"))
    if raw_flags != deterministic:
        raise SubmissionFormatError(
            f"parsed Reasoner row {row_number} risk_flags must use deterministic JSON encoding"
        )


def _read_exact_csv(
    path: Path,
    *,
    expected_fieldnames: tuple[str, ...],
    artifact_name: str,
) -> tuple[dict[str, str], ...]:
    try:
        with _open_utf8_csv_no_follow(path, artifact_name) as csv_file:
            reader = csv.reader(csv_file, strict=True)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise SubmissionFormatError(f"{artifact_name} is empty: {path}") from exc
            if tuple(header) != expected_fieldnames:
                raise SubmissionFormatError(
                    f"{artifact_name} header must be exactly: {', '.join(expected_fieldnames)}"
                )

            rows: list[dict[str, str]] = []
            for logical_row, values in enumerate(reader, start=2):
                if not values:
                    raise SubmissionFormatError(
                        f"{artifact_name} contains blank logical record {logical_row}"
                    )
                if len(values) != len(expected_fieldnames):
                    raise SubmissionFormatError(
                        f"{artifact_name} row {logical_row} has {len(values)} fields; "
                        f"expected {len(expected_fieldnames)}"
                    )
                rows.append(dict(zip(expected_fieldnames, values, strict=True)))
    except SubmissionFormatError:
        raise
    except UnicodeDecodeError as exc:
        raise SubmissionFormatError(f"{artifact_name} is not valid UTF-8: {path}: {exc}") from exc
    except csv.Error as exc:
        raise SubmissionFormatError(f"{artifact_name} is malformed CSV: {path}: {exc}") from exc
    except OSError as exc:
        raise SubmissionFormatError(f"{artifact_name} could not be read: {path}: {exc}") from exc

    if not rows:
        raise SubmissionFormatError(f"{artifact_name} has no data rows: {path}")
    return tuple(rows)


def _open_utf8_csv_no_follow(path: Path, artifact_name: str):
    try:
        link_stat = path.lstat()
        if stat.S_ISLNK(link_stat.st_mode):
            raise SubmissionFormatError(f"{artifact_name} must not be a symlink: {path}")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        file_descriptor = os.open(path, flags)
    except SubmissionFormatError:
        raise
    except OSError as exc:
        raise SubmissionFormatError(f"{artifact_name} could not be read: {path}: {exc}") from exc

    try:
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise SubmissionFormatError(f"{artifact_name} must be a regular file: {path}")
        return open(file_descriptor, encoding="utf-8", newline="", closefd=True)
    except Exception:
        os.close(file_descriptor)
        raise


def _regular_file_identity(path: Path, artifact_name: str) -> FileIdentity:
    try:
        file_stat = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise SubmissionFormatError(
            f"{artifact_name} could not be inspected: {path}: {exc}"
        ) from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise SubmissionFormatError(f"{artifact_name} must be a regular file: {path}")
    return (file_stat.st_dev, file_stat.st_ino)


def _write_final_predictions_temp(
    run_path: Path,
    predictions: tuple[FinalPrediction, ...],
) -> Path:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{FINAL_PREDICTIONS_FILENAME}.",
            suffix=".tmp",
            dir=run_path,
            delete=False,
        ) as csv_file:
            temp_path = Path(csv_file.name)
            writer = csv.DictWriter(
                csv_file,
                fieldnames=list(FINAL_PREDICTIONS_FIELDNAMES),
                lineterminator="\n",
            )
            writer.writeheader()
            for prediction in predictions:
                writer.writerow(
                    {
                        "run_id": prediction.run_id,
                        "sample_id": prediction.sample_id,
                        "final_label": prediction.final_label,
                        "source_stage": prediction.source_stage,
                        "decision_reason": prediction.decision_reason,
                    }
                )
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def _read_final_predictions(
    path: Path,
    *,
    expected_run_id: str,
    expected_sample_ids: tuple[str, ...],
) -> tuple[FinalPrediction, ...]:
    rows = _read_exact_csv(
        path,
        expected_fieldnames=FINAL_PREDICTIONS_FIELDNAMES,
        artifact_name="final predictions artifact",
    )
    predictions: list[FinalPrediction] = []
    for row_number, row in enumerate(rows, start=2):
        if row["run_id"] != expected_run_id:
            raise SubmissionFormatError(
                f"final predictions row {row_number} run_id does not match expected run_id"
            )
        if row["final_label"] not in VALID_LABELS:
            raise SubmissionFormatError(
                f"final predictions row {row_number} final_label must be exactly 0, 1, or 2"
            )
        if row["source_stage"] not in VALID_SOURCE_STAGES:
            raise SubmissionFormatError(
                f"final predictions row {row_number} source_stage is invalid"
            )
        if (
            not row["decision_reason"].strip()
            or row["decision_reason"] != row["decision_reason"].strip()
        ):
            raise SubmissionFormatError(
                f"final predictions row {row_number} decision_reason must be non-empty"
            )
        predictions.append(
            FinalPrediction(
                run_id=row["run_id"],
                sample_id=row["sample_id"],
                final_label=cast(ReasonerLabel, row["final_label"]),
                source_stage=cast(FinalSourceStage, row["source_stage"]),
                decision_reason=row["decision_reason"],
            )
        )

    actual_ids = tuple(prediction.sample_id for prediction in predictions)
    if actual_ids != expected_sample_ids:
        raise SubmissionFormatError(
            "final predictions ordered sample IDs do not match the official test set"
        )
    return tuple(predictions)


def _read_submission(
    path: Path,
    *,
    expected_predictions: tuple[FinalPrediction, ...],
) -> None:
    rows = _read_exact_csv(
        path,
        expected_fieldnames=SUBMISSION_FIELDNAMES,
        artifact_name="Multimodal submission artifact",
    )
    actual = tuple((row["sample_id"], row["label"]) for row in rows)
    expected = tuple(
        (prediction.sample_id, prediction.final_label) for prediction in expected_predictions
    )
    if actual != expected:
        raise SubmissionFormatError(
            "Multimodal submission artifact does not match validated final predictions"
        )


def _write_submission_temp(
    run_path: Path,
    predictions: tuple[FinalPrediction, ...],
) -> Path:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{SUBMISSION_FILENAME}.",
            suffix=".tmp",
            dir=run_path,
            delete=False,
        ) as csv_file:
            temp_path = Path(csv_file.name)
            writer = csv.DictWriter(
                csv_file,
                fieldnames=list(SUBMISSION_FIELDNAMES),
                lineterminator="\n",
            )
            writer.writeheader()
            for prediction in predictions:
                writer.writerow(
                    {"sample_id": prediction.sample_id, "label": prediction.final_label}
                )
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def _publish_artifact_pair(
    final_temp: Path,
    final_path: Path,
    submission_temp: Path,
    submission_path: Path,
    *,
    final_identity: FileIdentity,
    submission_identity: FileIdentity,
) -> None:
    final_published = False
    try:
        if (
            _regular_file_identity(final_temp, "staged final predictions artifact")
            != final_identity
        ):
            raise SubmissionFormatError(
                "staged final predictions artifact changed before publication"
            )
        try:
            os.link(final_temp, final_path)
        except FileExistsError as exc:
            raise SubmissionFormatError(
                f"submission artifact already exists: {final_path}"
            ) from exc
        final_published = True
        if (
            _regular_file_identity(submission_temp, "staged Multimodal submission artifact")
            != submission_identity
        ):
            raise SubmissionFormatError(
                "staged Multimodal submission artifact changed before publication"
            )
        try:
            os.link(submission_temp, submission_path)
        except FileExistsError as exc:
            raise SubmissionFormatError(
                f"submission artifact already exists: {submission_path}"
            ) from exc
    except Exception as publish_exc:
        if final_published:
            try:
                _remove_owned_publication(final_temp, final_path)
            except SubmissionFormatError as rollback_exc:
                raise rollback_exc from publish_exc
        raise


def _remove_owned_publication(source_temp: Path, destination: Path) -> None:
    try:
        if not destination.exists():
            return
        if os.path.samefile(source_temp, destination):
            destination.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise SubmissionFormatError(
            "published artifact could not be rolled back after publication failure: "
            f"{destination}: {exc}"
        ) from exc


def _cleanup_temp_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except FileNotFoundError:
        return
    except OSError:
        return


def _validate_run_id_value(value: object, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or "\0" in value
        or "/" in value
        or "\\" in value
        or value in {".", ".."}
    ):
        raise SubmissionFormatError(f"{field_name} must be one non-empty path-safe directory name")
    _require_utf8(value, field_name)


def _require_utf8(value: str, field_name: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise SubmissionFormatError(f"{field_name} contains invalid Unicode data") from exc
