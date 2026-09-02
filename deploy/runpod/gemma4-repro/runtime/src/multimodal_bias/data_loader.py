"""Data loading boundary for official Multimodal inputs."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from multimodal_bias.exceptions import DataLayoutError
from multimodal_bias.schemas import DataLayoutReport, SampleRecord

DEFAULT_DATA_ROOT = Path("data/raw/open")

REQUIRED_DIRECTORIES = (
    "train",
    "train/images",
    "test",
    "test/images",
)

REQUIRED_FILES = (
    "train/train.csv",
    "test/test.csv",
    "sample_submission.csv",
)

TRAIN_COLUMNS = ("sample_id", "image_path", "context", "question", "answers", "label")
TEST_COLUMNS = ("sample_id", "image_path", "context", "question", "answers")
SAMPLE_SUBMISSION_COLUMNS = ("sample_id", "label")
VALID_LABELS = {"0", "1", "2"}


@dataclass(frozen=True)
class _CsvValidationResult:
    row_count: int
    sample_ids: tuple[str, ...]


def validate_data_layout(
    data_root: Path | str = DEFAULT_DATA_ROOT,
    *,
    allow_missing_test_images: bool = False,
) -> DataLayoutReport:
    """Validate the official Multimodal open.zip layout and return row-count metadata."""

    root = Path(data_root)
    errors: list[str] = []

    if not root.is_dir():
        errors.append(f"missing data root directory: {root}")
        _raise_if_errors(errors)

    for relative_dir in REQUIRED_DIRECTORIES:
        if not (root / relative_dir).is_dir():
            errors.append(f"missing required directory: {relative_dir}")

    for relative_file in REQUIRED_FILES:
        if not (root / relative_file).is_file():
            errors.append(f"missing required file: {relative_file}")

    _raise_if_errors(errors)

    resolved_root = root.resolve()
    train_result = _validate_csv(
        root=resolved_root,
        relative_csv_path="train/train.csv",
        required_columns=TRAIN_COLUMNS,
        required_non_empty_columns=TRAIN_COLUMNS,
        required_image_directory="train/images",
        require_existing_images=True,
        label_column="label",
        allow_empty_label=False,
        errors=errors,
    )
    test_result = _validate_csv(
        root=resolved_root,
        relative_csv_path="test/test.csv",
        required_columns=TEST_COLUMNS,
        required_non_empty_columns=TEST_COLUMNS,
        required_image_directory="test/images",
        require_existing_images=not allow_missing_test_images,
        label_column=None,
        allow_empty_label=False,
        errors=errors,
    )
    sample_submission_result = _validate_csv(
        root=resolved_root,
        relative_csv_path="sample_submission.csv",
        required_columns=SAMPLE_SUBMISSION_COLUMNS,
        required_non_empty_columns=("sample_id",),
        required_image_directory=None,
        require_existing_images=False,
        label_column="label",
        allow_empty_label=True,
        errors=errors,
    )
    _validate_sample_submission_matches_test(
        test_sample_ids=test_result.sample_ids,
        sample_submission_ids=sample_submission_result.sample_ids,
        errors=errors,
    )

    _raise_if_errors(errors)

    return DataLayoutReport(
        data_root=resolved_root,
        train_rows=train_result.row_count,
        test_rows=test_result.row_count,
        sample_submission_rows=sample_submission_result.row_count,
    )


def load_test_records(
    data_root: Path | str = DEFAULT_DATA_ROOT,
    *,
    allow_missing_images: bool = False,
) -> tuple[SampleRecord, ...]:
    """Load validated Multimodal test.csv rows into typed sample records."""

    validate_data_layout(data_root, allow_missing_test_images=allow_missing_images)

    root = Path(data_root).resolve()
    relative_csv_path = "test/test.csv"
    csv_path = root / relative_csv_path
    records: list[SampleRecord] = []
    errors: list[str] = []

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row_number, row in enumerate(reader, start=2):
                answers = _parse_answers(
                    relative_csv_path=relative_csv_path,
                    row_number=row_number,
                    raw_answers=row.get("answers", ""),
                    errors=errors,
                )
                if answers is None:
                    continue

                records.append(
                    SampleRecord(
                        sample_id=(row.get("sample_id") or "").strip(),
                        image_path=_resolve_image_path(
                            root=root,
                            relative_csv_path=relative_csv_path,
                            raw_image_path=row.get("image_path", ""),
                            required_image_directory="test/images",
                        ),
                        context=row.get("context") or "",
                        question=row.get("question") or "",
                        answers=answers,
                        row_number=row_number,
                    )
                )
    except UnicodeDecodeError as exc:
        errors.append(f"{relative_csv_path} is not readable as UTF-8: {exc}")
    except OSError as exc:
        errors.append(f"{relative_csv_path} could not be read: {exc}")
    except csv.Error as exc:
        errors.append(f"{relative_csv_path} is not a valid CSV file: {exc}")

    _raise_if_errors(errors)
    return tuple(records)


def _validate_csv(
    *,
    root: Path,
    relative_csv_path: str,
    required_columns: tuple[str, ...],
    required_non_empty_columns: tuple[str, ...],
    required_image_directory: str | None,
    require_existing_images: bool,
    label_column: str | None,
    allow_empty_label: bool,
    errors: list[str],
) -> _CsvValidationResult:
    csv_path = root / relative_csv_path

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = reader.fieldnames or []
            duplicate_columns = _find_duplicates(fieldnames)
            if duplicate_columns:
                errors.append(
                    f"{relative_csv_path} has duplicate columns: {', '.join(duplicate_columns)}"
                )
            missing_columns = [column for column in required_columns if column not in fieldnames]
            if missing_columns:
                errors.append(
                    f"{relative_csv_path} missing required columns: {', '.join(missing_columns)}"
                )
                return _CsvValidationResult(row_count=0, sample_ids=())

            row_count = 0
            sample_ids: list[str] = []
            seen_sample_ids: set[str] = set()
            for row_number, row in enumerate(reader, start=2):
                row_count += 1
                if None in row:
                    errors.append(f"{relative_csv_path} row {row_number} has extra unnamed fields")
                _validate_required_fields(
                    relative_csv_path=relative_csv_path,
                    row_number=row_number,
                    row=row,
                    required_non_empty_columns=required_non_empty_columns,
                    errors=errors,
                )
                sample_id = (row.get("sample_id") or "").strip()
                if sample_id:
                    if sample_id in seen_sample_ids:
                        errors.append(
                            f"{relative_csv_path} row {row_number} has duplicate sample_id: "
                            f"{sample_id}"
                        )
                    else:
                        seen_sample_ids.add(sample_id)
                        sample_ids.append(sample_id)
                if required_image_directory is not None:
                    _validate_image_path(
                        root=root,
                        relative_csv_path=relative_csv_path,
                        row_number=row_number,
                        raw_image_path=row.get("image_path", ""),
                        required_image_directory=required_image_directory,
                        require_existing_image=require_existing_images,
                        errors=errors,
                    )
                if label_column is not None:
                    _validate_label(
                        relative_csv_path=relative_csv_path,
                        row_number=row_number,
                        label=row.get(label_column, ""),
                        allow_empty_label=allow_empty_label,
                        errors=errors,
                    )
            if row_count == 0:
                errors.append(f"{relative_csv_path} has no data rows")
            return _CsvValidationResult(row_count=row_count, sample_ids=tuple(sample_ids))
    except UnicodeDecodeError as exc:
        errors.append(f"{relative_csv_path} is not readable as UTF-8: {exc}")
    except OSError as exc:
        errors.append(f"{relative_csv_path} could not be read: {exc}")
    except csv.Error as exc:
        errors.append(f"{relative_csv_path} is not a valid CSV file: {exc}")

    return _CsvValidationResult(row_count=0, sample_ids=())


def _parse_answers(
    *,
    relative_csv_path: str,
    row_number: int,
    raw_answers: str,
    errors: list[str],
) -> tuple[str, str, str] | None:
    try:
        parsed_answers = json.loads(raw_answers)
    except json.JSONDecodeError as exc:
        errors.append(f"{relative_csv_path} row {row_number} has malformed answers JSON: {exc.msg}")
        return None

    if not isinstance(parsed_answers, list):
        errors.append(f"{relative_csv_path} row {row_number} answers must be a JSON list")
        return None

    if len(parsed_answers) != 3:
        errors.append(
            f"{relative_csv_path} row {row_number} must contain exactly 3 answers, "
            f"found {len(parsed_answers)}"
        )
        return None

    cleaned_answers: list[str] = []
    for answer_number, answer in enumerate(parsed_answers, start=1):
        if not isinstance(answer, str):
            errors.append(
                f"{relative_csv_path} row {row_number} answer {answer_number} must be a string"
            )
            return None

        cleaned_answer = answer.strip()
        if not cleaned_answer:
            errors.append(f"{relative_csv_path} row {row_number} answer {answer_number} is empty")
            return None
        cleaned_answers.append(cleaned_answer)

    return (cleaned_answers[0], cleaned_answers[1], cleaned_answers[2])


def _validate_required_fields(
    *,
    relative_csv_path: str,
    row_number: int,
    row: dict[str, str],
    required_non_empty_columns: tuple[str, ...],
    errors: list[str],
) -> None:
    for column in required_non_empty_columns:
        if not (row.get(column) or "").strip():
            errors.append(
                f"{relative_csv_path} row {row_number} has empty required field: {column}"
            )


def _validate_image_path(
    *,
    root: Path,
    relative_csv_path: str,
    row_number: int,
    raw_image_path: str | None,
    required_image_directory: str,
    require_existing_image: bool,
    errors: list[str],
) -> None:
    image_value = (raw_image_path or "").strip()
    if not image_value:
        return
    image_path = Path(image_value)

    if image_path.is_absolute():
        errors.append(
            f"{relative_csv_path} row {row_number} has absolute image_path: {image_value}"
        )
        return
    if ".." in image_path.parts:
        errors.append(
            f"{relative_csv_path} row {row_number} has escaping image_path: {image_value}"
        )
        return

    resolved_image_path = _resolve_image_path(
        root=root,
        relative_csv_path=relative_csv_path,
        raw_image_path=image_value,
        required_image_directory=required_image_directory,
    )
    required_image_root = (root / required_image_directory).resolve(strict=False)
    try:
        resolved_image_path.relative_to(root)
    except ValueError:
        errors.append(
            f"{relative_csv_path} row {row_number} has escaping image_path: {image_value}"
        )
        return
    try:
        resolved_image_path.relative_to(required_image_root)
    except ValueError:
        errors.append(
            f"{relative_csv_path} row {row_number} image_path is not under "
            f"{required_image_directory}: {image_value}"
        )
        return

    if require_existing_image and not resolved_image_path.is_file():
        errors.append(
            f"{relative_csv_path} row {row_number} image_path does not exist: {image_value}"
        )


def _resolve_image_path(
    *,
    root: Path,
    relative_csv_path: str,
    raw_image_path: str | None,
    required_image_directory: str,
) -> Path:
    image_path = Path((raw_image_path or "").strip())
    root_relative_path = (root / image_path).resolve(strict=False)
    required_image_root = (root / required_image_directory).resolve(strict=False)
    try:
        root_relative_path.relative_to(required_image_root)
    except ValueError:
        csv_relative_path = (root / relative_csv_path).parent / image_path
        return csv_relative_path.resolve(strict=False)
    return root_relative_path


def _validate_label(
    *,
    relative_csv_path: str,
    row_number: int,
    label: str | None,
    allow_empty_label: bool,
    errors: list[str],
) -> None:
    stripped_label = (label or "").strip()
    if stripped_label == "":
        if allow_empty_label:
            return
        return

    if stripped_label not in VALID_LABELS:
        errors.append(f"{relative_csv_path} row {row_number} has invalid label: {stripped_label!r}")


def _validate_sample_submission_matches_test(
    *,
    test_sample_ids: tuple[str, ...],
    sample_submission_ids: tuple[str, ...],
    errors: list[str],
) -> None:
    if test_sample_ids == sample_submission_ids:
        return

    if len(test_sample_ids) != len(sample_submission_ids):
        errors.append(
            "sample_submission.csv row count does not match test/test.csv: "
            f"{len(sample_submission_ids)} != {len(test_sample_ids)}"
        )
        return

    for row_offset, (test_sample_id, submission_sample_id) in enumerate(
        zip(test_sample_ids, sample_submission_ids, strict=True),
        start=2,
    ):
        if test_sample_id != submission_sample_id:
            errors.append(
                "sample_submission.csv sample_id mismatch at row "
                f"{row_offset}: {submission_sample_id} != {test_sample_id}"
            )
            return


def _find_duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def _raise_if_errors(errors: list[str]) -> None:
    if errors:
        raise DataLayoutError("Invalid Multimodal data layout:\n- " + "\n- ".join(errors))
