import csv
import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import multimodal_bias.submission as submission_module
from multimodal_bias.exceptions import SubmissionFormatError
from multimodal_bias.parsing import PARSED_REASONER_FIELDNAMES
from multimodal_bias.schemas import FinalPrediction, SubmissionResult
from multimodal_bias.submission import (
    FINAL_PREDICTIONS_FIELDNAMES,
    SUBMISSION_FIELDNAMES,
    generate_submission_artifacts,
    generate_submission_artifacts_from_predictions,
    resolve_run_directory,
)

RUN_ID = "20260618_120000_candidate"


def _valid_parsed_row(
    sample_id: str,
    label: str = "2",
    **overrides: str,
) -> dict[str, str]:
    row = {
        "run_id": RUN_ID,
        "sample_id": sample_id,
        "parsed_label": label,
        "uncertainty_option_index": "2",
        "evidence_summary": '근거, with a quoted "value"\nand newline',
        "evidence_type": "insufficient_evidence",
        "uncertainty_signal": "true",
        "risk_flags": "[]",
        "schema_version": "reasoner_output_v3",
        "parse_status": "valid",
        "parse_error": "",
    }
    row.update(overrides)
    if label != row["uncertainty_option_index"] and "evidence_type" not in overrides:
        row["evidence_type"] = "objective_visible_evidence"
        row["uncertainty_signal"] = "false"
    return row


def _write_parsed_artifact(
    path: Path,
    rows: list[dict[str, str]],
    *,
    fieldnames: tuple[str, ...] = PARSED_REASONER_FIELDNAMES,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=list(fieldnames),
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader.fieldnames or []), list(reader)


def _build_run(tmp_path: Path) -> tuple[Path, Path]:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    parsed_path = run_dir / "parsed_reasoner.csv"
    return run_dir, parsed_path


def test_resolve_run_directory_accepts_one_existing_run_directory(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    run_dir = runs_root / RUN_ID
    run_dir.mkdir(parents=True)

    assert resolve_run_directory(runs_root, RUN_ID) == run_dir.resolve()


@pytest.mark.parametrize(
    "run_id",
    [
        "",
        " candidate",
        "candidate ",
        "../outside",
        "/absolute",
        "nested/run",
        "nested\\run",
        ".",
        "..",
        "bad\0id",
    ],
)
def test_resolve_run_directory_rejects_unsafe_run_ids(
    tmp_path: Path,
    run_id: str,
) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    with pytest.raises(SubmissionFormatError, match="run_id"):
        resolve_run_directory(runs_root, run_id)


def test_resolve_run_directory_rejects_missing_and_symlinked_runs(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    with pytest.raises(SubmissionFormatError, match="does not exist"):
        resolve_run_directory(runs_root, "missing-run")

    real_run = tmp_path / "outside-run"
    real_run.mkdir()
    linked_run = runs_root / "linked-run"
    linked_run.symlink_to(real_run, target_is_directory=True)

    with pytest.raises(SubmissionFormatError, match="symlink"):
        resolve_run_directory(runs_root, "linked-run")


def test_final_prediction_and_submission_result_are_frozen_typed_contracts(
    tmp_path: Path,
) -> None:
    prediction = FinalPrediction(
        run_id="20260618_120000_candidate",
        sample_id="test_0000",
        final_label="2",
        source_stage="reasoner",
        decision_reason="validated_reasoner_output",
    )
    result = SubmissionResult(
        final_predictions_path=tmp_path / "final_predictions.csv",
        submission_path=tmp_path / "submission.csv",
        predictions=(prediction,),
        total_samples=1,
    )

    assert result.predictions == (prediction,)
    assert result.total_samples == 1
    with pytest.raises(FrozenInstanceError):
        prediction.final_label = "0"  # type: ignore[misc]


def test_generate_submission_artifacts_writes_exact_ordered_utf8_csvs(
    tmp_path: Path,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    rows = [
        _valid_parsed_row(
            "테스트_0000",
            "0",
            risk_flags='["protected_attribute_risk"]',
        ),
        _valid_parsed_row("test_0001", "2"),
    ]
    _write_parsed_artifact(parsed_path, rows)
    source_bytes = parsed_path.read_bytes()
    raw_path = run_dir / "raw_reasoner.jsonl"
    raw_path.write_bytes(b'{"immutable":true}\n')
    raw_bytes = raw_path.read_bytes()

    result = generate_submission_artifacts(
        parsed_path,
        run_dir,
        expected_run_id=RUN_ID,
        expected_sample_ids=("테스트_0000", "test_0001"),
    )

    assert result.total_samples == 2
    assert result.predictions == (
        FinalPrediction(
            run_id=RUN_ID,
            sample_id="테스트_0000",
            final_label="0",
            source_stage="reasoner",
            decision_reason="validated_reasoner_output",
        ),
        FinalPrediction(
            run_id=RUN_ID,
            sample_id="test_0001",
            final_label="2",
            source_stage="reasoner",
            decision_reason="validated_reasoner_output",
        ),
    )
    final_header, final_rows = _read_csv(result.final_predictions_path)
    submission_header, submission_rows = _read_csv(result.submission_path)
    assert final_header == list(FINAL_PREDICTIONS_FIELDNAMES)
    assert [row["sample_id"] for row in final_rows] == ["테스트_0000", "test_0001"]
    assert [row["final_label"] for row in final_rows] == ["0", "2"]
    assert submission_header == list(SUBMISSION_FIELDNAMES) == ["sample_id", "label"]
    assert submission_rows == [
        {"sample_id": "테스트_0000", "label": "0"},
        {"sample_id": "test_0001", "label": "2"},
    ]
    assert parsed_path.read_bytes() == source_bytes
    assert raw_path.read_bytes() == raw_bytes


def test_generate_submission_from_predictions_accepts_verifier_and_arbitration_sources(
    tmp_path: Path,
) -> None:
    run_dir, _parsed_path = _build_run(tmp_path)
    predictions = (
        FinalPrediction(
            run_id=RUN_ID,
            sample_id="test_0000",
            final_label="1",
            source_stage="verifier",
            decision_reason="verifier_concrete_defect_with_objective_support",
        ),
        FinalPrediction(
            run_id=RUN_ID,
            sample_id="test_0001",
            final_label="2",
            source_stage="arbitration",
            decision_reason="both_outputs_lack_objective_support",
        ),
    )

    result = generate_submission_artifacts_from_predictions(
        predictions,
        run_dir,
        expected_run_id=RUN_ID,
        expected_sample_ids=("test_0000", "test_0001"),
    )

    assert result.predictions == predictions
    final_header, final_rows = _read_csv(result.final_predictions_path)
    submission_header, submission_rows = _read_csv(result.submission_path)
    assert final_header == list(FINAL_PREDICTIONS_FIELDNAMES)
    assert [row["source_stage"] for row in final_rows] == ["verifier", "arbitration"]
    assert [row["decision_reason"] for row in final_rows] == [
        "verifier_concrete_defect_with_objective_support",
        "both_outputs_lack_objective_support",
    ]
    assert submission_header == list(SUBMISSION_FIELDNAMES)
    assert submission_rows == [
        {"sample_id": "test_0000", "label": "1"},
        {"sample_id": "test_0001", "label": "2"},
    ]


@pytest.mark.parametrize(
    ("prediction", "error_fragment"),
    [
        (
            FinalPrediction(
                run_id="other",
                sample_id="test_0000",
                final_label="2",
                source_stage="reasoner",
                decision_reason="validated_reasoner_output",
            ),
            "run_id",
        ),
        (
            FinalPrediction(
                run_id=RUN_ID,
                sample_id="test_9999",
                final_label="2",
                source_stage="reasoner",
                decision_reason="validated_reasoner_output",
            ),
            "ordered",
        ),
        (
            FinalPrediction(
                run_id=RUN_ID,
                sample_id="test_0000",
                final_label="3",  # type: ignore[arg-type]
                source_stage="reasoner",
                decision_reason="validated_reasoner_output",
            ),
            "final_label",
        ),
        (
            FinalPrediction(
                run_id=RUN_ID,
                sample_id="test_0000",
                final_label="2",
                source_stage="unknown",  # type: ignore[arg-type]
                decision_reason="validated_reasoner_output",
            ),
            "source_stage",
        ),
        (
            FinalPrediction(
                run_id=RUN_ID,
                sample_id="test_0000",
                final_label="2",
                source_stage="reasoner",
                decision_reason="",
            ),
            "decision_reason",
        ),
    ],
)
def test_generate_submission_from_predictions_rejects_invalid_prediction_contract(
    tmp_path: Path,
    prediction: FinalPrediction,
    error_fragment: str,
) -> None:
    run_dir, _parsed_path = _build_run(tmp_path)

    with pytest.raises(SubmissionFormatError, match=error_fragment):
        generate_submission_artifacts_from_predictions(
            (prediction,),
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )

    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()


def test_generate_submission_rejects_staged_final_prediction_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])

    def write_changed_final(
        run_path: Path,
        predictions: tuple[FinalPrediction, ...],
    ) -> Path:
        temp_path = run_path / ".final_predictions.csv.changed.tmp"
        with temp_path.open("w", encoding="utf-8", newline="") as csv_file:
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
                        "final_label": "1",
                        "source_stage": prediction.source_stage,
                        "decision_reason": prediction.decision_reason,
                    }
                )
        return temp_path

    monkeypatch.setattr(submission_module, "_write_final_predictions_temp", write_changed_final)

    with pytest.raises(SubmissionFormatError, match="does not match"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )

    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()
    assert list(run_dir.glob(".*.tmp")) == []


def test_generate_submission_does_not_mask_success_when_temp_cleanup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])
    real_unlink = Path.unlink

    def fail_temp_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path.parent == run_dir and path.name.startswith("."):
            raise OSError("injected cleanup failure")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_temp_unlink)

    result = generate_submission_artifacts(
        parsed_path,
        run_dir,
        expected_run_id=RUN_ID,
        expected_sample_ids=("test_0000",),
    )

    assert result.total_samples == 1
    assert (run_dir / "final_predictions.csv").is_file()
    assert (run_dir / "submission.csv").is_file()


@pytest.mark.parametrize(
    "expected_sample_ids",
    [None, "test_0000", 42],
)
def test_generate_submission_rejects_invalid_expected_sample_ids(
    tmp_path: Path,
    expected_sample_ids: object,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])

    with pytest.raises(SubmissionFormatError, match="expected sample IDs"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=expected_sample_ids,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "expected_run_id",
    ["", " candidate", "../outside", "bad\0id"],
)
def test_generate_submission_rejects_unsafe_expected_run_ids(
    tmp_path: Path,
    expected_run_id: str,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])

    with pytest.raises(SubmissionFormatError, match="expected run_id"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=expected_run_id,
            expected_sample_ids=("test_0000",),
        )


@pytest.mark.parametrize(
    ("overrides", "error_fragment"),
    [
        ({"parsed_label": ""}, "parsed_label"),
        ({"parsed_label": " 0 "}, "parsed_label"),
        ({"parsed_label": "3"}, "parsed_label"),
        ({"parsed_label": "-1"}, "parsed_label"),
        ({"evidence_summary": "   "}, "evidence_summary"),
        ({"evidence_type": "appearance"}, "evidence_type"),
        ({"uncertainty_signal": "True"}, "uncertainty_signal"),
        ({"risk_flags": '["invalid_parse"]'}, "risk_flags"),
        ({"risk_flags": '[ "protected_attribute_risk" ]'}, "deterministic"),
        ({"parse_status": "source_failed"}, "parse_status"),
        ({"parse_error": "unexpected"}, "parse_error"),
        ({"run_id": "another-run"}, "run_id"),
    ],
)
def test_generate_submission_rejects_invalid_parsed_row_contract(
    tmp_path: Path,
    overrides: dict[str, str],
    error_fragment: str,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000", **overrides)])

    with pytest.raises(SubmissionFormatError, match=error_fragment):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )

    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()


@pytest.mark.parametrize(
    "parse_status",
    [
        "source_failed",
        "missing_marker",
        "invalid_json",
        "invalid_schema",
        "invalid_label",
    ],
)
def test_generate_submission_rejects_every_non_valid_parse_status(
    tmp_path: Path,
    parse_status: str,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(
        parsed_path,
        [
            _valid_parsed_row(
                "test_0000",
                parse_status=parse_status,
                parse_error="model output could not be parsed",
            )
        ],
    )

    with pytest.raises(SubmissionFormatError):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )

    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()
    assert list(run_dir.glob(".*.tmp")) == []


@pytest.mark.parametrize(
    ("rows", "expected_ids", "error_fragment"),
    [
        (
            [_valid_parsed_row("test_0000"), _valid_parsed_row("test_0000")],
            ("test_0000",),
            "duplicate",
        ),
        (
            [_valid_parsed_row("test_0001"), _valid_parsed_row("test_0000")],
            ("test_0000", "test_0001"),
            "ordered",
        ),
        (
            [_valid_parsed_row("test_0000"), _valid_parsed_row("test_0001")],
            ("test_0000",),
            "ordered",
        ),
        ([_valid_parsed_row("test_0000")], ("test_0000", "test_0001"), "ordered"),
    ],
)
def test_generate_submission_rejects_sample_lineage_mismatch(
    tmp_path: Path,
    rows: list[dict[str, str]],
    expected_ids: tuple[str, ...],
    error_fragment: str,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, rows)

    with pytest.raises(SubmissionFormatError, match=error_fragment):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=expected_ids,
        )


def test_generate_submission_rejects_noncanonical_header_and_blank_record(
    tmp_path: Path,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    duplicate_header = list(PARSED_REASONER_FIELDNAMES)
    duplicate_header[-1] = "parse_status"
    _write_parsed_artifact(
        parsed_path,
        [_valid_parsed_row("test_0000")],
        fieldnames=tuple(duplicate_header),
    )

    with pytest.raises(SubmissionFormatError, match="header"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )


@pytest.mark.parametrize(
    "header_kind",
    ["missing", "extra", "unnamed_header", "extra_unnamed_field"],
)
def test_generate_submission_rejects_header_shape_variants(
    tmp_path: Path,
    header_kind: str,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    header = list(PARSED_REASONER_FIELDNAMES)
    values = [
        RUN_ID,
        "test_0000",
        "2",
        "evidence",
        "insufficient_evidence",
        "true",
        "[]",
        "valid",
        "",
    ]
    if header_kind == "missing":
        header.pop()
        values.pop()
    elif header_kind == "extra":
        header.append("extra")
        values.append("value")
    elif header_kind == "unnamed_header":
        header.append("")
        values.append("unnamed")
    else:
        values.append("unnamed")
    parsed_path.write_text(
        ",".join(header) + "\n" + ",".join(values) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SubmissionFormatError, match="header|fields"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )


def test_generate_submission_rejects_missing_parsed_artifact(tmp_path: Path) -> None:
    run_dir, parsed_path = _build_run(tmp_path)

    with pytest.raises(SubmissionFormatError, match="does not exist"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )

    parsed_path.write_text(
        ",".join(PARSED_REASONER_FIELDNAMES) + "\n\n",
        encoding="utf-8",
    )
    with pytest.raises(SubmissionFormatError, match="blank|no data"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )


@pytest.mark.parametrize("source_kind", ["empty", "malformed", "invalid_utf8"])
def test_generate_submission_rejects_unreadable_source_content(
    tmp_path: Path,
    source_kind: str,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    if source_kind == "empty":
        parsed_path.write_bytes(b"")
    elif source_kind == "malformed":
        parsed_path.write_text('run_id,sample_id\n"unterminated', encoding="utf-8")
    else:
        parsed_path.write_bytes(b"\xff\xfe")

    with pytest.raises(SubmissionFormatError):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )


def test_generate_submission_wraps_source_read_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])
    real_os_open = os.open

    def fail_target_open(path: Path, flags: int) -> int:
        if Path(path) == parsed_path:
            raise OSError("injected unreadable parsed artifact")
        return real_os_open(path, flags)

    monkeypatch.setattr(submission_module.os, "open", fail_target_open)

    with pytest.raises(SubmissionFormatError, match="could not be read"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )


def test_generate_submission_rejects_noncanonical_paths_and_existing_outputs(
    tmp_path: Path,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])

    with pytest.raises(SubmissionFormatError, match="directly inside|canonical"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
            final_predictions_path=tmp_path / "final_predictions.csv",
        )

    with pytest.raises(SubmissionFormatError, match="directly inside|canonical"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
            submission_path=tmp_path / "submission.csv",
        )

    existing_final = run_dir / "final_predictions.csv"
    existing_final.write_text("keep-final", encoding="utf-8")
    with pytest.raises(SubmissionFormatError, match="already exists"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )
    assert existing_final.read_text(encoding="utf-8") == "keep-final"
    assert not (run_dir / "submission.csv").exists()
    existing_final.unlink()

    existing = run_dir / "submission.csv"
    existing.write_text("keep", encoding="utf-8")
    with pytest.raises(SubmissionFormatError, match="already exists"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )
    assert existing.read_text(encoding="utf-8") == "keep"
    assert not (run_dir / "final_predictions.csv").exists()


def test_generate_submission_cleans_temps_when_second_stage_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])

    def fail_submission_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected submission write failure")

    monkeypatch.setattr(submission_module, "_write_submission_temp", fail_submission_write)

    with pytest.raises(OSError, match="injected"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )

    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()
    assert list(run_dir.glob(".*.tmp")) == []


def test_generate_submission_cleans_state_when_first_stage_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])

    def fail_final_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected final write failure")

    monkeypatch.setattr(submission_module, "_write_final_predictions_temp", fail_final_write)

    with pytest.raises(OSError, match="injected"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )
    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()
    assert list(run_dir.glob(".*.tmp")) == []


def test_generate_submission_rolls_back_own_first_publication_on_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])
    real_link = os.link
    link_calls = 0

    def race_on_second_link(source: Path, destination: Path) -> None:
        nonlocal link_calls
        link_calls += 1
        if link_calls == 2:
            Path(destination).write_text("concurrent", encoding="utf-8")
        real_link(source, destination)

    monkeypatch.setattr(submission_module.os, "link", race_on_second_link)

    with pytest.raises(SubmissionFormatError, match="already exists"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )

    assert not (run_dir / "final_predictions.csv").exists()
    assert (run_dir / "submission.csv").read_text(encoding="utf-8") == "concurrent"
    assert list(run_dir.glob(".*.tmp")) == []


def test_generate_submission_rolls_back_first_publication_on_second_link_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])
    real_link = os.link
    link_calls = 0

    def fail_second_link(source: Path, destination: Path) -> None:
        nonlocal link_calls
        link_calls += 1
        if link_calls == 2:
            raise OSError("injected second publication failure")
        real_link(source, destination)

    monkeypatch.setattr(submission_module.os, "link", fail_second_link)

    with pytest.raises(OSError, match="injected second"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )
    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()
    assert list(run_dir.glob(".*.tmp")) == []


def test_generate_submission_reports_rollback_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])
    real_link = os.link
    real_unlink = Path.unlink
    link_calls = 0

    def fail_second_link(source: Path, destination: Path) -> None:
        nonlocal link_calls
        link_calls += 1
        if link_calls == 2:
            raise OSError("injected second publication failure")
        real_link(source, destination)

    def fail_final_rollback(path: Path, *args: object, **kwargs: object) -> None:
        if path == run_dir / "final_predictions.csv":
            raise OSError("injected rollback cleanup failure")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(submission_module.os, "link", fail_second_link)
    monkeypatch.setattr(Path, "unlink", fail_final_rollback)

    with pytest.raises(SubmissionFormatError, match="could not be rolled back"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )


def test_generate_submission_preserves_concurrent_first_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])
    real_link = os.link

    def race_on_first_link(source: Path, destination: Path) -> None:
        Path(destination).write_text("concurrent-final", encoding="utf-8")
        real_link(source, destination)

    monkeypatch.setattr(submission_module.os, "link", race_on_first_link)

    with pytest.raises(SubmissionFormatError, match="already exists"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )
    assert (run_dir / "final_predictions.csv").read_text(encoding="utf-8") == "concurrent-final"
    assert not (run_dir / "submission.csv").exists()
    assert list(run_dir.glob(".*.tmp")) == []


def test_generate_submission_rejects_symlinked_run_and_parsed_artifact(
    tmp_path: Path,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    _write_parsed_artifact(parsed_path, [_valid_parsed_row("test_0000")])
    linked_run = tmp_path / "linked-run"
    linked_run.symlink_to(run_dir, target_is_directory=True)

    with pytest.raises(SubmissionFormatError, match="symlink|run directory name"):
        generate_submission_artifacts(
            linked_run / "parsed_reasoner.csv",
            linked_run,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )

    real_parsed = run_dir / "real.csv"
    parsed_path.rename(real_parsed)
    parsed_path.symlink_to(real_parsed)
    with pytest.raises(SubmissionFormatError, match="directly inside"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )


def test_generate_submission_rejects_symlinked_parsed_artifact_at_read_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, parsed_path = _build_run(tmp_path)
    real_parsed = run_dir / "real_parsed_reasoner.csv"
    _write_parsed_artifact(real_parsed, [_valid_parsed_row("test_0000")])
    parsed_path.symlink_to(real_parsed)
    real_is_symlink = Path.is_symlink

    def hide_target_symlink(path: Path) -> bool:
        if path == parsed_path:
            return False
        return real_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", hide_target_symlink)

    with pytest.raises(SubmissionFormatError, match="symlink"):
        generate_submission_artifacts(
            parsed_path,
            run_dir,
            expected_run_id=RUN_ID,
            expected_sample_ids=("test_0000",),
        )
