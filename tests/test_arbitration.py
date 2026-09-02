import json
from pathlib import Path

import pytest

from multimodal_bias.arbitration import (
    arbitrate_final_predictions,
    read_verification_artifact,
)
from multimodal_bias.exceptions import SubmissionFormatError
from multimodal_bias.schemas import (
    FinalPrediction,
    ParsedReasonerRecord,
    VerificationRecord,
)

RUN_ID = "run_001"


def _reasoner_record(
    sample_id: str = "test_0000",
    *,
    label: str | None = "0",
    evidence_type: str | None = "stated_text_fact",
    uncertainty_signal: bool | None = False,
    parse_status: str = "valid",
    parse_error: str | None = None,
) -> ParsedReasonerRecord:
    return ParsedReasonerRecord(
        run_id=RUN_ID,
        sample_id=sample_id,
        parsed_label=label,  # type: ignore[arg-type]
        evidence_summary="The context states the first answer is correct."
        if label is not None
        else None,
        evidence_type=evidence_type,  # type: ignore[arg-type]
        uncertainty_signal=uncertainty_signal,
        risk_flags=(),
        parse_status=parse_status,  # type: ignore[arg-type]
        parse_error=parse_error,
    )


def _verification_record(
    sample_id: str = "test_0000",
    *,
    status: str = "verified",
    requires_verification: bool = True,
    before_label: str | None = "0",
    after_label: str | None = "1",
    reasoner_defect_found: bool | None = True,
    objective_support: bool | None = True,
    verifier_evidence_type: str | None = "stated_text_fact",
    verifier_reason: str | None = "The context explicitly supports answer 1.",
    triggers: tuple[str, ...] = ("protected_attribute_risk",),
    raw_verifier_output: str | None = "FINAL_VERIFICATION_JSON: {}",
    image_status: str | None = "loaded",
    verifier_parse_status: str | None = "valid",
    error_type: str | None = None,
    error_message: str | None = None,
) -> VerificationRecord:
    return VerificationRecord(
        run_id=RUN_ID,
        sample_id=sample_id,
        prompt_version="verifier_v1",
        triggers=triggers,  # type: ignore[arg-type]
        requires_verification=requires_verification,
        before_label=before_label,  # type: ignore[arg-type]
        raw_verifier_output=raw_verifier_output,
        after_label=after_label,  # type: ignore[arg-type]
        verifier_reason=verifier_reason,
        verifier_evidence_type=verifier_evidence_type,  # type: ignore[arg-type]
        reasoner_defect_found=reasoner_defect_found,
        objective_support=objective_support,
        image_status=image_status,  # type: ignore[arg-type]
        verifier_parse_status=verifier_parse_status,  # type: ignore[arg-type]
        generation_metadata=None,
        model_load_metadata=None,
        elapsed_seconds=0.1,
        status=status,  # type: ignore[arg-type]
        error_type=error_type,
        error_message=error_message,
    )


def _write_verification_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _record_to_json(record: VerificationRecord, **overrides: object) -> dict[str, object]:
    payload = {
        "run_id": record.run_id,
        "sample_id": record.sample_id,
        "prompt_version": record.prompt_version,
        "triggers": list(record.triggers),
        "requires_verification": record.requires_verification,
        "before_label": record.before_label,
        "raw_verifier_output": record.raw_verifier_output,
        "after_label": record.after_label,
        "verifier_reason": record.verifier_reason,
        "verifier_evidence_type": record.verifier_evidence_type,
        "reasoner_defect_found": record.reasoner_defect_found,
        "objective_support": record.objective_support,
        "image_status": record.image_status,
        "verifier_parse_status": record.verifier_parse_status,
        "generation_metadata": record.generation_metadata,
        "model_load_metadata": record.model_load_metadata,
        "elapsed_seconds": record.elapsed_seconds,
        "status": record.status,
        "error_type": record.error_type,
        "error_message": record.error_message,
    }
    payload.update(overrides)
    return payload


def test_arbitration_keeps_reasoner_when_verifier_finds_no_concrete_defect() -> None:
    predictions = arbitrate_final_predictions(
        (_reasoner_record(label="0"),),
        (
            _verification_record(
                after_label="1",
                reasoner_defect_found=False,
                objective_support=True,
            ),
        ),
    )

    assert predictions == (
        FinalPrediction(
            run_id=RUN_ID,
            sample_id="test_0000",
            final_label="0",
            source_stage="reasoner",
            decision_reason="verifier_no_concrete_defect_keep_reasoner",
        ),
    )


def test_arbitration_flips_only_with_concrete_defect_and_objective_support() -> None:
    predictions = arbitrate_final_predictions(
        (_reasoner_record(label="0"),),
        (
            _verification_record(
                after_label="1", reasoner_defect_found=True, objective_support=True
            ),
        ),
    )

    assert predictions[0] == FinalPrediction(
        run_id=RUN_ID,
        sample_id="test_0000",
        final_label="1",
        source_stage="verifier",
        decision_reason="verifier_concrete_defect_with_objective_support",
    )


def test_arbitration_chooses_uncertain_when_both_outputs_lack_objective_support() -> None:
    predictions = arbitrate_final_predictions(
        (
            _reasoner_record(
                label="0",
                evidence_type="insufficient_evidence",
                uncertainty_signal=True,
            ),
        ),
        (
            _verification_record(
                after_label="2",
                reasoner_defect_found=True,
                objective_support=False,
                verifier_evidence_type="insufficient_evidence",
            ),
        ),
    )

    assert predictions[0] == FinalPrediction(
        run_id=RUN_ID,
        sample_id="test_0000",
        final_label="2",
        source_stage="arbitration",
        decision_reason="both_outputs_lack_objective_support",
    )


def test_arbitration_rejects_invalid_reasoner_without_generated_verifier_candidate() -> None:
    with pytest.raises(SubmissionFormatError, match="no valid generated candidate"):
        arbitrate_final_predictions(
            (
                _reasoner_record(
                    label=None,
                    evidence_type=None,
                    uncertainty_signal=None,
                    parse_status="invalid_json",
                    parse_error="bad json",
                ),
            ),
            (
                _verification_record(
                    status="parse_failed",
                    before_label=None,
                    after_label=None,
                    reasoner_defect_found=None,
                    objective_support=None,
                    verifier_evidence_type=None,
                    verifier_reason=None,
                    raw_verifier_output="bad verifier output",
                    verifier_parse_status="invalid_json",
                    error_type="ParseError",
                    error_message="invalid verifier json",
                ),
            ),
        )


def test_arbitration_keeps_valid_reasoner_when_verifier_failure_has_no_usable_support() -> None:
    predictions = arbitrate_final_predictions(
        (_reasoner_record(label="1"),),
        (
            _verification_record(
                status="inference_failed",
                before_label="1",
                after_label=None,
                reasoner_defect_found=None,
                objective_support=None,
                verifier_evidence_type=None,
                verifier_reason=None,
                raw_verifier_output=None,
                verifier_parse_status=None,
                error_type="InferenceError",
                error_message="model failed",
            ),
        ),
    )

    assert predictions[0] == FinalPrediction(
        run_id=RUN_ID,
        sample_id="test_0000",
        final_label="1",
        source_stage="reasoner",
        decision_reason="verifier_no_usable_support_keep_reasoner",
    )


def test_arbitration_rejects_missing_or_misaligned_verification_rows() -> None:
    with pytest.raises(SubmissionFormatError, match="ordered"):
        arbitrate_final_predictions(
            (_reasoner_record("test_0000"), _reasoner_record("test_0001")),
            (_verification_record("test_0001"),),
        )


def test_read_verification_artifact_accepts_exact_ordered_records(tmp_path: Path) -> None:
    path = tmp_path / "verification.jsonl"
    _write_verification_jsonl(
        path,
        [
            _record_to_json(
                _verification_record(
                    "test_0000",
                    status="skipped_not_triggered",
                    requires_verification=False,
                    after_label=None,
                    reasoner_defect_found=None,
                    objective_support=None,
                    verifier_evidence_type=None,
                    verifier_reason=None,
                    triggers=(),
                    raw_verifier_output=None,
                    image_status=None,
                    verifier_parse_status=None,
                )
            ),
            _record_to_json(_verification_record("test_0001")),
        ],
    )

    records = read_verification_artifact(
        path,
        expected_run_id=RUN_ID,
        expected_sample_ids=("test_0000", "test_0001"),
    )

    assert [record.sample_id for record in records] == ["test_0000", "test_0001"]
    assert records[0].status == "skipped_not_triggered"
    assert records[1].after_label == "1"


@pytest.mark.parametrize(
    ("overrides", "error_fragment"),
    [
        ({"run_id": "other"}, "run_id"),
        ({"sample_id": "test_9999"}, "ordered"),
        ({"after_label": "3"}, "after_label"),
        ({"status": "unknown"}, "status"),
        ({"requires_verification": "true"}, "requires_verification"),
        ({"elapsed_seconds": -0.1}, "elapsed_seconds"),
        ({"triggers": ["not_a_trigger"]}, "triggers"),
        ({"status": "verified", "after_label": None}, "after_label"),
        (
            {
                "status": "parse_failed",
                "after_label": None,
                "verifier_reason": None,
                "verifier_evidence_type": None,
                "reasoner_defect_found": None,
                "objective_support": None,
                "verifier_parse_status": "invalid_json",
                "error_type": None,
            },
            "error_type",
        ),
    ],
)
def test_read_verification_artifact_rejects_invalid_rows(
    tmp_path: Path,
    overrides: dict[str, object],
    error_fragment: str,
) -> None:
    path = tmp_path / "verification.jsonl"
    _write_verification_jsonl(path, [_record_to_json(_verification_record(), **overrides)])

    with pytest.raises(SubmissionFormatError, match=error_fragment):
        read_verification_artifact(
            path,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )


def test_read_verification_artifact_rejects_duplicate_rows(tmp_path: Path) -> None:
    path = tmp_path / "verification.jsonl"
    _write_verification_jsonl(
        path,
        [_record_to_json(_verification_record()), _record_to_json(_verification_record())],
    )

    with pytest.raises(SubmissionFormatError, match="duplicate"):
        read_verification_artifact(
            path,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000", "test_0001"),
        )
