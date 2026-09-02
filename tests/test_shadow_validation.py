import io
import json
from pathlib import Path

import pytest
from PIL import Image

from multimodal_bias.exceptions import ShadowValidationError
from multimodal_bias.validation import (
    audit_shadow_records,
    evaluate_shadow_predictions,
    freeze_shadow_dataset,
    load_shadow_records,
)


def _png(index: int) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (2, 2), (index % 255, (index // 255) % 255, 0)).save(stream, format="PNG")
    return stream.getvalue()


SUBSETS = [
    "ambiguous",
    "disambiguated_text",
    "visual_grounded",
    "elimination",
    "stereotype_trap",
    "expression_trap",
    "role_or_function",
    "parsing_stress",
]


def _write_corpus(root: Path, count: int = 300, pending: bool = False) -> tuple[Path, Path]:
    image_root = root / "source"
    image_root.mkdir(parents=True)
    rows = []
    for index in range(count):
        image_name = f"image-{index:04d}.png"
        (image_root / image_name).write_bytes(_png(index))
        position = index % 3
        ambiguous = index < 120
        label = position if ambiguous else (position + 1) % 3
        rows.append(
            {
                "sample_id": f"shadow-{index:04d}",
                "image_ref": image_name,
                "context": f"Independent context {index}",
                "question": "Which option follows from the evidence?",
                "answers": ["Person A", "Person B", "Cannot be determined"],
                "expected_label": label,
                "uncertainty_option_index": position,
                "expected_is_uncertainty": ambiguous,
                "subsets": SUBSETS,
                "provenance_type": "self_authored",
                "source_uri_or_note": f"Independent authoring batch {index}",
                "license_or_permission": "Author-owned validation material",
                "author_id": "author-1",
                "review_status": "pending" if pending else "reviewed",
                "reviewer_id": None if pending else "reviewer-2",
                "split": "sealed_holdout" if index < 120 else "selection",
                "randomization_seed": index,
            }
        )
    dataset = root / "records.jsonl"
    dataset.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return dataset, image_root


def _write_predictions(path: Path, frozen_dir: Path, split: str) -> None:
    rows = [
        json.loads(line)
        for line in (frozen_dir / "dataset.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    selected = [row for row in rows if row["split"] == split]
    path.write_text(
        "".join(
            json.dumps(
                {
                    "sample_id": row["sample_id"],
                    "predicted_label": row["expected_label"],
                    "elapsed_seconds": 0.5,
                    "parse_valid": True,
                    "image_loaded": True,
                    "unresolved": False,
                },
                sort_keys=True,
            )
            + "\n"
            for row in selected
        ),
        encoding="utf-8",
    )


def test_audit_reports_pending_and_coverage_failures(tmp_path: Path) -> None:
    dataset, image_root = _write_corpus(tmp_path, count=10, pending=True)

    report = audit_shadow_records(load_shadow_records(dataset, image_root))

    assert report.promotion_ready is False
    assert report.reviewed_count == 0
    assert "record count must be between 300 and 600" in report.violations
    assert "all frozen records must be reviewed or adjudicated" in report.violations


def test_loader_rejects_test_derived_provenance(tmp_path: Path) -> None:
    dataset, image_root = _write_corpus(tmp_path, count=1)
    row = json.loads(dataset.read_text(encoding="utf-8"))
    row["source_uri_or_note"] = "Copied from data/raw/open/test/test.csv"
    dataset.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ShadowValidationError, match="evaluation/test-derived"):
        load_shadow_records(dataset, image_root)


def test_loader_rejects_self_review_and_image_escape(tmp_path: Path) -> None:
    dataset, image_root = _write_corpus(tmp_path, count=1)
    row = json.loads(dataset.read_text(encoding="utf-8"))
    row["reviewer_id"] = row["author_id"]
    dataset.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ShadowValidationError, match="independent reviewer"):
        load_shadow_records(dataset, image_root)

    row["reviewer_id"] = "reviewer-2"
    row["image_ref"] = "../outside.png"
    (tmp_path / "outside.png").write_bytes(_png(999))
    dataset.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ShadowValidationError, match="escapes image root"):
        load_shadow_records(dataset, image_root)


def test_freeze_and_sealed_evaluation_are_hash_bound_and_aggregate_only(tmp_path: Path) -> None:
    dataset, image_root = _write_corpus(tmp_path)
    frozen = tmp_path / "frozen-v1"

    freeze = freeze_shadow_dataset(dataset, image_root, frozen, "shadow-v1")

    assert freeze.record_count == 300
    assert freeze.manifest_path.is_file()
    predictions = tmp_path / "predictions.jsonl"
    _write_predictions(predictions, frozen, "sealed_holdout")
    result = evaluate_shadow_predictions(
        frozen,
        predictions,
        tmp_path / "metrics.json",
        "candidate-a",
        "sealed_holdout",
    )
    assert result.metrics["accuracy"] == 1.0
    assert result.metrics["balanced_accuracy"] == 1.0
    assert result.metrics["sealed_aggregate_only"] is True
    metrics_text = result.metrics_path.read_text(encoding="utf-8")
    assert "shadow-0000" not in metrics_text
    assert "context" not in metrics_text

    with pytest.raises(ShadowValidationError, match="overwrite"):
        freeze_shadow_dataset(dataset, image_root, frozen, "shadow-v1")

    with (frozen / "dataset.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    with pytest.raises(ShadowValidationError, match="hash mismatch"):
        evaluate_shadow_predictions(
            frozen,
            predictions,
            tmp_path / "metrics-2.json",
            "candidate-a",
            "sealed_holdout",
        )


def test_evaluation_rejects_prediction_order_mismatch(tmp_path: Path) -> None:
    dataset, image_root = _write_corpus(tmp_path)
    frozen = tmp_path / "frozen-v1"
    freeze_shadow_dataset(dataset, image_root, frozen, "shadow-v1")
    predictions = tmp_path / "predictions.jsonl"
    _write_predictions(predictions, frozen, "selection")
    rows = predictions.read_text(encoding="utf-8").splitlines()
    predictions.write_text("\n".join(reversed(rows)) + "\n", encoding="utf-8")

    with pytest.raises(ShadowValidationError, match="IDs/order"):
        evaluate_shadow_predictions(
            frozen,
            predictions,
            tmp_path / "metrics.json",
            "candidate-a",
            "selection",
        )
