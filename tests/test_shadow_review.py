import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from multimodal_bias.cli import app
from multimodal_bias.exceptions import ShadowValidationError
from multimodal_bias.shadow_review import apply_shadow_reviews
from multimodal_bias.validation import audit_shadow_records, load_shadow_records

SUBSET_COUNTS = {
    "ambiguous": 120,
    "disambiguated_text": 90,
    "visual_grounded": 90,
    "elimination": 75,
    "stereotype_trap": 75,
    "expression_trap": 60,
    "role_or_function": 60,
    "parsing_stress": 30,
}
EVIDENCE_BY_SUBSET = {
    "ambiguous": "insufficient_evidence",
    "disambiguated_text": "stated_text_fact",
    "visual_grounded": "objective_visual_evidence",
    "elimination": "valid_elimination",
    "stereotype_trap": "stated_text_fact",
    "expression_trap": "stated_text_fact",
    "role_or_function": "stated_text_fact",
    "parsing_stress": "valid_elimination",
}


def _png(index: int) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (2, 2), (index % 251, (index // 251) % 251, 17)).save(stream, format="PNG")
    return stream.getvalue()


def _write_pending(root: Path) -> tuple[Path, Path, list[dict[str, object]]]:
    image_root = root / "shadow"
    image_dir = image_root / "images"
    image_dir.mkdir(parents=True)
    subsets = [subset for subset, count in SUBSET_COUNTS.items() for _ in range(count)]
    rows: list[dict[str, object]] = []
    for index, subset in enumerate(subsets):
        image_ref = f"images/{index:04d}.png"
        (image_root / image_ref).write_bytes(_png(index))
        position = index % 3
        is_ambiguous = subset == "ambiguous"
        label = position if is_ambiguous else (position + 1) % 3
        rows.append(
            {
                "sample_id": f"shadow-{index:04d}",
                "image_ref": image_ref,
                "context": f"Independent context {index}",
                "question": "Which option is supported?",
                "answers": ["Person A", "Person B", "Cannot be determined"],
                "expected_label": label,
                "uncertainty_option_index": position,
                "expected_is_uncertainty": is_ambiguous,
                "subsets": [subset],
                "provenance_type": "generated_allowed",
                "source_uri_or_note": f"Independent source {index}",
                "license_or_permission": "Permitted validation material",
                "author_id": "codex-independent-authoring-v1",
                "review_status": "pending",
                "reviewer_id": None,
                "split": "sealed_holdout" if index < 180 else "selection",
                "randomization_seed": 236722600,
            }
        )
    dataset = root / "records.jsonl"
    _write_jsonl(dataset, rows)
    return dataset, image_root, rows


def _decisions(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "sample_id": row["sample_id"],
            "reviewer_id": "human-reviewer-v1",
            "independent_label": row["expected_label"],
            "proposed_label": row["expected_label"],
            "decision": "reviewed",
            "evidence_basis": EVIDENCE_BY_SUBSET[str(row["subsets"][0])],
            "evidence_note": f"Independent evidence for {row['sample_id']}",
            "natural_language_ok": True,
            "protected_attribute_shortcut_absent": True,
            "content_safety_ok": True,
        }
        for row in rows
    ]


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def test_complete_review_is_applied_in_base_order_and_passes_audit(tmp_path: Path) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    decisions = _write_jsonl(tmp_path / "decisions.jsonl", _decisions(rows))

    result = apply_shadow_reviews(dataset, image_root, decisions, tmp_path / "review-v1")

    assert result.report.promotion_ready is True
    assert result.report.input_record_count == 600
    assert result.report.decision_count == 600
    assert result.report.reviewed_count == 600
    assert result.report.unresolved_count == 0
    reviewed = load_shadow_records(result.reviewed_path, image_root)
    assert [record.sample_id for record in reviewed] == [row["sample_id"] for row in rows]
    assert all(record.review_status == "reviewed" for record in reviewed)
    assert audit_shadow_records(reviewed).promotion_ready is True
    assert result.history_path.is_file()
    assert result.manifest_path.is_file()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    for filename, digest in manifest["output_sha256"].items():
        assert hashlib.sha256((result.output_dir / filename).read_bytes()).hexdigest() == digest


def test_partial_pilot_writes_evidence_but_is_not_promotion_ready(tmp_path: Path) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    decisions = _write_jsonl(tmp_path / "pilot.jsonl", _decisions(rows)[:30])

    result = apply_shadow_reviews(dataset, image_root, decisions, tmp_path / "pilot-output")

    assert result.report.promotion_ready is False
    assert result.report.decision_count == 30
    assert result.report.missing_decision_count == 570
    assert result.report.unresolved_count == 570
    assert "all 600 input records require a terminal review decision" in result.report.violations


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda values, rows: values.append(dict(values[0])), "duplicate sample_id"),
        (
            lambda values, rows: values[0].update({"sample_id": "shadow-extra"}),
            "unknown sample_id",
        ),
        (
            lambda values, rows: values[0].update(
                {"reviewer_id": "codex-independent-authoring-v1"}
            ),
            "independent reviewer",
        ),
        (
            lambda values, rows: values[0].update({"proposed_label": 2}),
            "proposed_label",
        ),
        (
            lambda values, rows: values[120].update(
                {"independent_label": rows[120]["uncertainty_option_index"]}
            ),
            "matching independent_label",
        ),
        (
            lambda values, rows: values[0].update({"content_safety_ok": False}),
            "quality checks",
        ),
        (
            lambda values, rows: values[0].update({"unexpected": True}),
            "unknown fields",
        ),
    ],
)
def test_malformed_or_tampered_reviews_fail_without_output(
    tmp_path: Path, mutate: object, message: str
) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    values = _decisions(rows)
    mutate(values, rows)  # type: ignore[operator]
    decisions = _write_jsonl(tmp_path / "decisions.jsonl", values)
    output = tmp_path / "review-v1"

    with pytest.raises(ShadowValidationError, match=message):
        apply_shadow_reviews(dataset, image_root, decisions, output)

    assert not output.exists()


def test_adjudication_can_explicitly_change_label_and_subsets(tmp_path: Path) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    values = _decisions(rows)
    target = rows[120]
    values[120].update(
        {
            "independent_label": target["uncertainty_option_index"],
            "decision": "adjudication_required",
            "evidence_basis": "insufficient_evidence",
        }
    )
    decisions = _write_jsonl(tmp_path / "decisions.jsonl", values)
    adjudications = _write_jsonl(
        tmp_path / "adjudications.jsonl",
        [
            {
                "sample_id": target["sample_id"],
                "adjudicator_id": "human-adjudicator-v1",
                "decision": "adjudicated",
                "final_label": target["uncertainty_option_index"],
                "final_subsets": ["ambiguous"],
                "evidence_basis": "insufficient_evidence",
                "evidence_note": "The image and text do not resolve the person.",
                "natural_language_ok": True,
                "protected_attribute_shortcut_absent": True,
                "content_safety_ok": True,
            }
        ],
    )

    result = apply_shadow_reviews(
        dataset,
        image_root,
        decisions,
        tmp_path / "review-v1",
        adjudications_path=adjudications,
    )

    assert result.report.promotion_ready is True
    changed = next(
        row
        for row in map(json.loads, result.reviewed_path.read_text().splitlines())
        if row["sample_id"] == target["sample_id"]
    )
    assert changed["review_status"] == "adjudicated"
    assert changed["expected_label"] == target["uncertainty_option_index"]
    assert changed["expected_is_uncertainty"] is True
    assert changed["subsets"] == ["ambiguous"]
    history = result.history_path.read_text(encoding="utf-8")
    assert '"before_expected_label"' in history
    assert '"after_expected_label"' in history


def test_adjudicator_must_differ_from_author_and_reviewer(tmp_path: Path) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    values = _decisions(rows)
    values[120]["decision"] = "adjudication_required"
    decisions = _write_jsonl(tmp_path / "decisions.jsonl", values)
    adjudications = _write_jsonl(
        tmp_path / "adjudications.jsonl",
        [
            {
                "sample_id": rows[120]["sample_id"],
                "adjudicator_id": "human-reviewer-v1",
                "decision": "rejected",
                "final_label": rows[120]["expected_label"],
                "final_subsets": rows[120]["subsets"],
                "evidence_basis": EVIDENCE_BY_SUBSET[str(rows[120]["subsets"][0])],
                "evidence_note": "Reject after independent adjudication.",
                "natural_language_ok": True,
                "protected_attribute_shortcut_absent": True,
                "content_safety_ok": True,
            }
        ],
    )

    with pytest.raises(ShadowValidationError, match="adjudicator.*reviewer"):
        apply_shadow_reviews(
            dataset,
            image_root,
            decisions,
            tmp_path / "review-v1",
            adjudications_path=adjudications,
        )


def test_rejections_remain_auditable_and_coverage_failure_is_reported(tmp_path: Path) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    values = _decisions(rows)
    for value in values[:120]:
        value["decision"] = "rejected"
    decisions = _write_jsonl(tmp_path / "decisions.jsonl", values)

    result = apply_shadow_reviews(dataset, image_root, decisions, tmp_path / "review-v1")

    assert result.report.promotion_ready is False
    assert result.report.rejected_count == 120
    assert result.report.retained_count == 480
    assert any("ambiguous" in violation for violation in result.report.violations)
    assert len(result.rejections_path.read_text().splitlines()) == 120
    assert "shadow-0000" in result.rejections_path.read_text()


def test_output_is_no_clobber(tmp_path: Path) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    decisions = _write_jsonl(tmp_path / "pilot.jsonl", _decisions(rows)[:1])
    output = tmp_path / "review-v1"
    apply_shadow_reviews(dataset, image_root, decisions, output)

    with pytest.raises(ShadowValidationError, match="overwrite"):
        apply_shadow_reviews(dataset, image_root, decisions, output)


def test_duplicate_base_ids_and_non_utf8_decisions_fail_closed(tmp_path: Path) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    dataset_rows = [json.loads(line) for line in dataset.read_text().splitlines()]
    dataset_rows[-1]["sample_id"] = dataset_rows[0]["sample_id"]
    _write_jsonl(dataset, dataset_rows)
    decisions = _write_jsonl(tmp_path / "decisions.jsonl", _decisions(rows))
    with pytest.raises(ShadowValidationError, match="duplicate sample_id in pending dataset"):
        apply_shadow_reviews(dataset, image_root, decisions, tmp_path / "duplicate-output")

    valid_dataset, valid_image_root, _ = _write_pending(tmp_path / "valid")
    invalid_utf8 = tmp_path / "invalid-utf8.jsonl"
    invalid_utf8.write_bytes(b"\xff\xfe")
    with pytest.raises(ShadowValidationError, match="must be UTF-8"):
        apply_shadow_reviews(
            valid_dataset,
            valid_image_root,
            invalid_utf8,
            tmp_path / "utf8-output",
        )


def test_cli_writes_partial_report_and_exits_nonzero(tmp_path: Path) -> None:
    dataset, image_root, rows = _write_pending(tmp_path)
    decisions = _write_jsonl(tmp_path / "pilot.jsonl", _decisions(rows)[:1])
    output = tmp_path / "pilot-output"

    result = CliRunner().invoke(
        app,
        [
            "shadow-apply-reviews",
            "--dataset",
            str(dataset),
            "--image-root",
            str(image_root),
            "--decisions",
            str(decisions),
            "--output-dir",
            str(output),
        ],
    )

    assert result.exit_code == 1
    assert "promotion_ready=false" in result.output
    assert (output / "report.json").is_file()


def test_review_html_exports_canonical_fields_and_handles_load_errors() -> None:
    html = Path("data/shadow-private/pending-v1/review.html").read_text(encoding="utf-8")

    for field in (
        "evidence_basis",
        "content_safety_ok",
        "protected_attribute_shortcut_absent",
        "natural_language_ok",
    ):
        assert field in html
    assert ".catch(" in html
    assert "adjudication_required" in html
    assert "disabled" in html
    assert "approve.disabled=answer!==r.expected_label||!shortcut.checked" in html
    assert "review-ko-translations.json" in html


def test_korean_review_translations_cover_every_visible_dataset_phrase() -> None:
    translations_path = Path("configs/validation/review-ko-translations.json")
    translations = json.loads(translations_path.read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in Path("data/shadow-private/pending-v1/records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert set(translations) == {"answers", "contexts", "questions"}
    assert {row["context"] for row in rows} == set(translations["contexts"])
    assert {row["question"] for row in rows} == set(translations["questions"])
    assert {answer for row in rows for answer in row["answers"]} == set(translations["answers"])
    assert all(
        isinstance(korean, str) and korean.strip()
        for group in translations.values()
        for korean in group.values()
    )
