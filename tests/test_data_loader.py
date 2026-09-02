import csv
import json
from pathlib import Path

import pytest

from multimodal_bias.data_loader import load_test_records, validate_data_layout
from multimodal_bias.exceptions import DataLayoutError
from multimodal_bias.schemas import SampleRecord


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_valid_open_layout(tmp_path: Path) -> Path:
    data_root = tmp_path / "open"
    (data_root / "train/images").mkdir(parents=True)
    (data_root / "test/images").mkdir(parents=True)
    (data_root / "train/images/train_img_0000.jpg").write_bytes(b"train-image")
    (data_root / "test/images/test_img_0000.jpg").write_bytes(b"test-image")

    answers = json.dumps(["first person", "second person", "uncertain"])
    _write_csv(
        data_root / "train/train.csv",
        ["sample_id", "image_path", "context", "question", "answers", "label"],
        [
            {
                "sample_id": "train_0000",
                "image_path": "train/images/train_img_0000.jpg",
                "context": "A training context.",
                "question": "Who is described?",
                "answers": answers,
                "label": "0",
            }
        ],
    )
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        [
            {
                "sample_id": "test_0000",
                "image_path": "test/images/test_img_0000.jpg",
                "context": "A test context.",
                "question": "Who is described?",
                "answers": answers,
            }
        ],
    )
    _write_csv(
        data_root / "sample_submission.csv",
        ["sample_id", "label"],
        [{"sample_id": "test_0000", "label": "0"}],
    )
    return data_root


def test_validate_data_layout_accepts_valid_official_layout(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)

    report = validate_data_layout(data_root)

    assert report.data_root == data_root.resolve()
    assert report.train_rows == 1
    assert report.test_rows == 1
    assert report.sample_submission_rows == 1


def test_load_test_records_returns_typed_records_in_csv_order(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)

    records = load_test_records(data_root)

    assert records == (
        SampleRecord(
            sample_id="test_0000",
            image_path=(data_root / "test/images/test_img_0000.jpg").resolve(),
            context="A test context.",
            question="Who is described?",
            answers=("first person", "second person", "uncertain"),
            row_number=2,
        ),
    )


def test_load_test_records_preserves_multiple_row_order(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    (data_root / "test/images/test_img_0001.jpg").write_bytes(b"test-image-2")
    answers = json.dumps(["first person", "second person", "uncertain"])
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        [
            {
                "sample_id": "test_0000",
                "image_path": "test/images/test_img_0000.jpg",
                "context": "A first test context.",
                "question": "Who is described first?",
                "answers": answers,
            },
            {
                "sample_id": "test_0001",
                "image_path": "test/images/test_img_0001.jpg",
                "context": "A second test context.",
                "question": "Who is described second?",
                "answers": answers,
            },
        ],
    )
    _write_csv(
        data_root / "sample_submission.csv",
        ["sample_id", "label"],
        [
            {"sample_id": "test_0000", "label": "0"},
            {"sample_id": "test_0001", "label": "1"},
        ],
    )

    records = load_test_records(data_root)

    assert [record.sample_id for record in records] == ["test_0000", "test_0001"]
    assert [record.row_number for record in records] == [2, 3]


def test_load_test_records_accepts_csv_relative_image_paths(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    answers = json.dumps(["first person", "second person", "uncertain"])
    _write_csv(
        data_root / "train/train.csv",
        ["sample_id", "image_path", "context", "question", "answers", "label"],
        [
            {
                "sample_id": "train_0000",
                "image_path": "./images/train_img_0000.jpg",
                "context": "A training context.",
                "question": "Who is described?",
                "answers": answers,
                "label": "0",
            }
        ],
    )
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        [
            {
                "sample_id": "test_0000",
                "image_path": "./images/test_img_0000.jpg",
                "context": "A test context.",
                "question": "Who is described?",
                "answers": answers,
            }
        ],
    )

    records = load_test_records(data_root)

    assert records[0].image_path == (data_root / "test/images/test_img_0000.jpg").resolve()


@pytest.mark.parametrize(
    ("answers", "match"),
    [
        ("not json", "malformed answers JSON"),
        (json.dumps({"first": "person"}), "answers must be a JSON list"),
        (json.dumps(["first person", "second person"]), "exactly 3 answers"),
        (
            json.dumps(["first person", "second person", "uncertain", "none"]),
            "exactly 3 answers",
        ),
        (json.dumps(["first person", 2, "uncertain"]), "answer 2 must be a string"),
        (json.dumps(["first person", "   ", "uncertain"]), "answer 2 is empty"),
    ],
)
def test_load_test_records_rejects_invalid_answers(
    tmp_path: Path,
    answers: str,
    match: str,
) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        [
            {
                "sample_id": "test_0000",
                "image_path": "test/images/test_img_0000.jpg",
                "context": "A test context.",
                "question": "Who is described?",
                "answers": answers,
            }
        ],
    )

    with pytest.raises(DataLayoutError, match=match) as exc_info:
        load_test_records(data_root)

    assert "test/test.csv row 2" in str(exc_info.value)


def test_load_test_records_reuses_layout_validation(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    (data_root / "test/images/test_img_0000.jpg").unlink()

    with pytest.raises(DataLayoutError, match="image_path does not exist"):
        load_test_records(data_root)


def test_validate_data_layout_rejects_missing_required_file(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    (data_root / "test/test.csv").unlink()

    with pytest.raises(DataLayoutError, match="test/test.csv"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_missing_required_column(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question"],
        [
            {
                "sample_id": "test_0000",
                "image_path": "test/images/test_img_0000.jpg",
                "context": "A test context.",
                "question": "Who is described?",
            }
        ],
    )

    with pytest.raises(DataLayoutError, match="answers"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_missing_image_path_cell(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    (data_root / "test/test.csv").write_text(
        "sample_id,image_path,context,question,answers\ntest_0000\n",
        encoding="utf-8",
    )

    with pytest.raises(DataLayoutError, match="empty required field: image_path"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_missing_label_cell(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    (data_root / "train/train.csv").write_text(
        "sample_id,image_path,context,question,answers,label\n"
        "train_0000,train/images/train_img_0000.jpg,Context,Question,[]\n",
        encoding="utf-8",
    )

    with pytest.raises(DataLayoutError, match="empty required field: label"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_extra_unnamed_csv_fields(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    (data_root / "test/test.csv").write_text(
        "sample_id,image_path,context,question,answers\n"
        'test_0000,test/images/test_img_0000.jpg,Context,Question,"[]",extra\n',
        encoding="utf-8",
    )

    with pytest.raises(DataLayoutError, match="extra unnamed fields"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_non_utf8_csv(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    (data_root / "test/test.csv").write_bytes(b"\xff\xfe\x00")

    with pytest.raises(DataLayoutError, match="UTF-8"):
        validate_data_layout(data_root)


@pytest.mark.parametrize(
    "image_path",
    [
        "/tmp/test_img_0000.jpg",
        "../test/images/test_img_0000.jpg",
        "test/images/missing.jpg",
    ],
)
def test_validate_data_layout_rejects_malformed_image_paths(
    tmp_path: Path,
    image_path: str,
) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        [
            {
                "sample_id": "test_0000",
                "image_path": image_path,
                "context": "A test context.",
                "question": "Who is described?",
                "answers": json.dumps(["first person", "second person", "uncertain"]),
            }
        ],
    )

    with pytest.raises(DataLayoutError, match="image_path"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_wrong_split_image_path(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "train/train.csv",
        ["sample_id", "image_path", "context", "question", "answers", "label"],
        [
            {
                "sample_id": "train_0000",
                "image_path": "test/images/test_img_0000.jpg",
                "context": "A training context.",
                "question": "Who is described?",
                "answers": json.dumps(["first person", "second person", "uncertain"]),
                "label": "0",
            }
        ],
    )

    with pytest.raises(DataLayoutError, match="train/images"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_invalid_train_label(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "train/train.csv",
        ["sample_id", "image_path", "context", "question", "answers", "label"],
        [
            {
                "sample_id": "train_0000",
                "image_path": "train/images/train_img_0000.jpg",
                "context": "A training context.",
                "question": "Who is described?",
                "answers": json.dumps(["first person", "second person", "uncertain"]),
                "label": "7",
            }
        ],
    )

    with pytest.raises(DataLayoutError, match="label"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_invalid_sample_submission_label(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "sample_submission.csv",
        ["sample_id", "label"],
        [{"sample_id": "test_0000", "label": "7"}],
    )

    with pytest.raises(DataLayoutError, match="sample_submission.csv"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_sample_submission_id_mismatch(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "sample_submission.csv",
        ["sample_id", "label"],
        [{"sample_id": "wrong_0000", "label": "0"}],
    )

    with pytest.raises(DataLayoutError, match="sample_id mismatch"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_sample_submission_row_count_mismatch(
    tmp_path: Path,
) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "sample_submission.csv",
        ["sample_id", "label"],
        [],
    )

    with pytest.raises(DataLayoutError, match="row count"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_duplicate_sample_id(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    answers = json.dumps(["first person", "second person", "uncertain"])
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        [
            {
                "sample_id": "test_0000",
                "image_path": "test/images/test_img_0000.jpg",
                "context": "A test context.",
                "question": "Who is described?",
                "answers": answers,
            },
            {
                "sample_id": "test_0000",
                "image_path": "test/images/test_img_0000.jpg",
                "context": "A second test context.",
                "question": "Who is described?",
                "answers": answers,
            },
        ],
    )

    with pytest.raises(DataLayoutError, match="duplicate sample_id"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_duplicate_csv_headers(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    (data_root / "test/test.csv").write_text(
        "sample_id,image_path,context,question,answers,answers\n"
        'test_0000,test/images/test_img_0000.jpg,Context,Question,"[]","[]"\n',
        encoding="utf-8",
    )

    with pytest.raises(DataLayoutError, match="duplicate columns"):
        validate_data_layout(data_root)


def test_validate_data_layout_rejects_header_only_required_csv(tmp_path: Path) -> None:
    data_root = build_valid_open_layout(tmp_path)
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        [],
    )

    with pytest.raises(DataLayoutError, match="no data rows"):
        validate_data_layout(data_root)
