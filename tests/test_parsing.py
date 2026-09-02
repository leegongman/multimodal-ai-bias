import csv
import json
from pathlib import Path

import pytest

from multimodal_bias.exceptions import ParseError
from multimodal_bias.parsing import (
    PARSED_REASONER_FIELDNAMES,
    PARSED_REASONER_FILENAME,
    parse_reasoner_artifact,
    parse_reasoner_output,
    parse_verifier_output,
    read_parsed_reasoner_artifact,
)


def _final_output(payload: object) -> str:
    return "analysis before the answer\nFINAL_ANSWER_JSON: " + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "label": "2",
        "uncertainty_option_index": 2,
        "evidence": "The evidence does not identify either person.",
        "evidence_type": "insufficient_evidence",
        "uncertainty_signal": True,
        "protected_attribute_risk": False,
        "schema_version": "reasoner_output_v3",
    }
    payload.update(overrides)
    return payload


def _raw_row(
    sample_id: str,
    *,
    raw_output: str | None,
    status: object = "generated",
    run_id: str = "run_001",
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "sample_id": sample_id,
        "prompt_version": "reasoner_v3",
        "image_path": f"/tmp/{sample_id}.png",
        "image_status": "loaded" if status == "generated" else "missing",
        "raw_output": raw_output,
        "generation_metadata": None,
        "model_load_metadata": {"load_status": "loaded"},
        "elapsed_seconds": 0.01,
        "status": status,
        "error_type": None if status == "generated" else "InferenceError",
        "error_message": None if status == "generated" else "sample generation failed",
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _verifier_output(payload: object) -> str:
    return "independent analysis\nFINAL_VERIFICATION_JSON: " + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _verifier_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "label": "1",
        "reason": "The context explicitly identifies the second person.",
        "evidence_type": "stated_text_fact",
        "reasoner_defect_found": True,
        "objective_support": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("label", "evidence_type", "uncertainty_signal"),
    [
        ("0", "stated_text_fact", False),
        ("1", "objective_visible_evidence", False),
        ("0", "elimination", False),
        ("2", "insufficient_evidence", True),
    ],
)
def test_parse_reasoner_output_accepts_contract_values(
    label: str,
    evidence_type: str,
    uncertainty_signal: bool,
) -> None:
    record = parse_reasoner_output(
        _final_output(
            _valid_payload(
                label=label,
                evidence_type=evidence_type,
                uncertainty_signal=uncertainty_signal,
            )
        ),
        run_id="run_001",
        sample_id="sample_001",
    )

    assert record.run_id == "run_001"
    assert record.sample_id == "sample_001"
    assert record.parsed_label == label
    assert record.evidence_summary == "The evidence does not identify either person."
    assert record.evidence_type == evidence_type
    assert record.uncertainty_signal is uncertainty_signal
    assert record.risk_flags == ()
    assert record.parse_status == "valid"
    assert record.parse_error is None


def test_parse_reasoner_output_records_protected_attribute_risk() -> None:
    record = parse_reasoner_output(
        _final_output(_valid_payload(protected_attribute_risk=True)),
        run_id="run_001",
        sample_id="sample_001",
    )

    assert record.parse_status == "valid"
    assert record.risk_flags == ("protected_attribute_risk",)


def test_parse_reasoner_output_rejects_semantic_inconsistency() -> None:
    record = parse_reasoner_output(
        _final_output(
            _valid_payload(
                label="0",
                evidence_type="insufficient_evidence",
                uncertainty_signal=True,
            )
        ),
        run_id="run_001",
        sample_id="sample_001",
    )

    assert record.parse_status == "invalid_schema"
    assert record.parsed_label is None


@pytest.mark.parametrize(
    ("raw_output", "expected_status"),
    [
        ("no final marker", "missing_marker"),
        ("FINAL_ANSWER_JSON: ", "invalid_json"),
        ("FINAL_ANSWER_JSON: {bad json}", "invalid_json"),
        (
            'FINAL_ANSWER_JSON: {"label":"0","evidence":"x",'
            '"evidence_type":"elimination","uncertainty_signal":NaN,'
            '"protected_attribute_risk":false}',
            "invalid_json",
        ),
        ("FINAL_ANSWER_JSON: []", "invalid_schema"),
        (
            'FINAL_ANSWER_JSON: {"label":"0","label":"1","evidence":"x",'
            '"evidence_type":"elimination","uncertainty_signal":false,'
            '"protected_attribute_risk":false}',
            "invalid_json",
        ),
        (
            _final_output(
                {key: value for key, value in _valid_payload().items() if key != "evidence"}
            ),
            "invalid_schema",
        ),
        (_final_output(_valid_payload(extra="value")), "invalid_schema"),
        (_final_output(_valid_payload(evidence="   ")), "invalid_schema"),
        (_final_output(_valid_payload(evidence_type="appearance")), "invalid_schema"),
        (_final_output(_valid_payload(uncertainty_signal="true")), "invalid_schema"),
        (_final_output(_valid_payload(protected_attribute_risk=1)), "invalid_schema"),
        (_final_output(_valid_payload(label="3")), "invalid_label"),
        (_final_output(_valid_payload(label="-1")), "invalid_label"),
        (_final_output(_valid_payload(label=" 0 ")), "invalid_label"),
        (_final_output(_valid_payload(label=0)), "invalid_label"),
        (_final_output(_valid_payload(label=True)), "invalid_label"),
        (_final_output(_valid_payload(label=None)), "invalid_label"),
    ],
)
def test_parse_reasoner_output_rejects_invalid_generated_text(
    raw_output: str,
    expected_status: str,
) -> None:
    record = parse_reasoner_output(
        raw_output,
        run_id="run_001",
        sample_id="sample_001",
    )

    assert record.parsed_label is None
    assert record.evidence_summary is None
    assert record.evidence_type is None
    assert record.uncertainty_signal is None
    assert record.risk_flags == ("invalid_parse",)
    assert record.parse_status == expected_status
    assert record.parse_error


def test_parse_reasoner_output_requires_marker_on_final_non_empty_line() -> None:
    raw_output = _final_output(_valid_payload()) + "\ntrailing commentary\n"

    record = parse_reasoner_output(
        raw_output,
        run_id="run_001",
        sample_id="sample_001",
    )

    assert record.parse_status == "missing_marker"
    assert record.parsed_label is None


@pytest.mark.parametrize(
    "raw_output",
    [
        "FINAL_ANSWER_JSON: " + "[" * 1_100 + "]" * 1_100,
        "FINAL_ANSWER_JSON: " + "9" * 5_000,
    ],
)
def test_parse_reasoner_output_converts_json_resource_errors_to_invalid_rows(
    raw_output: str,
) -> None:
    record = parse_reasoner_output(
        raw_output,
        run_id="run_001",
        sample_id="sample_001",
    )

    assert record.parse_status == "invalid_json"
    assert record.parsed_label is None


def test_parse_reasoner_output_rejects_non_utf8_encodable_evidence() -> None:
    record = parse_reasoner_output(
        'FINAL_ANSWER_JSON: {"label":"0","uncertainty_option_index":2,"evidence":"\\ud800",'
        '"evidence_type":"elimination","uncertainty_signal":false,'
        '"protected_attribute_risk":false,"schema_version":"reasoner_output_v3"}',
        run_id="run_001",
        sample_id="sample_001",
    )

    assert record.parse_status == "invalid_schema"
    assert record.parsed_label is None


def test_parse_reasoner_artifact_writes_ordered_utf8_csv_and_source_failures(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    unicode_evidence = '가시적 표지, "STAFF"와\n행동이 역할을 확인한다.'
    _write_jsonl(
        raw_path,
        [
            _raw_row(
                "sample_001",
                raw_output=_final_output(
                    _valid_payload(
                        label="1",
                        evidence=unicode_evidence,
                        evidence_type="objective_visible_evidence",
                        uncertainty_signal=False,
                        protected_attribute_risk=True,
                    )
                ),
            ),
            _raw_row(
                "sample_002",
                raw_output=None,
                status="inference_failed",
            ),
            _raw_row("sample_003", raw_output="malformed output"),
        ],
    )

    result = parse_reasoner_artifact(raw_path)

    assert result.parsed_reasoner_path == tmp_path / PARSED_REASONER_FILENAME
    assert result.total_samples == 3
    assert result.valid_count == 1
    assert result.invalid_count == 2
    assert [record.sample_id for record in result.records] == [
        "sample_001",
        "sample_002",
        "sample_003",
    ]

    with result.parsed_reasoner_path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == list(PARSED_REASONER_FIELDNAMES)
    assert [row["sample_id"] for row in rows] == ["sample_001", "sample_002", "sample_003"]
    assert rows[0] == {
        "run_id": "run_001",
        "sample_id": "sample_001",
        "parsed_label": "1",
        "uncertainty_option_index": "2",
        "evidence_summary": unicode_evidence,
        "evidence_type": "objective_visible_evidence",
        "uncertainty_signal": "false",
        "risk_flags": '["protected_attribute_risk"]',
        "schema_version": "reasoner_output_v3",
        "parse_status": "valid",
        "parse_error": "",
    }
    assert rows[1]["parsed_label"] == ""
    assert rows[1]["risk_flags"] == '["invalid_parse"]'
    assert rows[1]["parse_status"] == "source_failed"
    assert "InferenceError" in rows[1]["parse_error"]
    assert rows[2]["parse_status"] == "missing_marker"


@pytest.mark.parametrize("status", ["image_failed", "prompt_failed", "inference_failed"])
def test_parse_reasoner_artifact_preserves_every_raw_source_failure(
    tmp_path: Path,
    status: str,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    _write_jsonl(raw_path, [_raw_row("sample_001", raw_output=None, status=status)])

    result = parse_reasoner_artifact(raw_path)

    assert result.records[0].parse_status == "source_failed"
    assert result.records[0].parsed_label is None
    assert result.records[0].risk_flags == ("invalid_parse",)


def test_parse_reasoner_artifact_converts_generated_row_without_raw_output_to_source_failure(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    _write_jsonl(raw_path, [_raw_row("sample_001", raw_output=None, status="generated")])

    result = parse_reasoner_artifact(raw_path)

    assert result.total_samples == 1
    assert result.valid_count == 0
    assert result.invalid_count == 1
    assert result.records[0].parse_status == "source_failed"
    assert result.records[0].parsed_label is None
    assert "raw_output" in result.records[0].parse_error


def test_parse_reasoner_artifact_rejects_prompt_version_schema_mismatch(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    row = _raw_row("sample_001", raw_output=_final_output(_valid_payload()))
    row["prompt_version"] = "reasoner_v2"
    _write_jsonl(raw_path, [row])

    with pytest.raises(ParseError, match="does not match schema_mode"):
        parse_reasoner_artifact(raw_path)


@pytest.mark.parametrize("status", [[], {}])
def test_parse_reasoner_artifact_rejects_unhashable_status_as_parse_error(
    tmp_path: Path,
    status: object,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    _write_jsonl(raw_path, [_raw_row("sample_001", raw_output=None, status=status)])

    with pytest.raises(ParseError, match="invalid status"):
        parse_reasoner_artifact(raw_path)


@pytest.mark.parametrize(
    "content",
    [
        "",
        "\n",
        "{bad json}\n",
        "[]\n",
        json.dumps(_raw_row("", raw_output=_final_output(_valid_payload()))) + "\n",
        (json.dumps(_raw_row("sample_001", raw_output=_final_output(_valid_payload()))) + "\n\n"),
        (
            json.dumps(_raw_row("sample_001", raw_output=_final_output(_valid_payload())))
            + "\n"
            + json.dumps(_raw_row("sample_001", raw_output=_final_output(_valid_payload())))
            + "\n"
        ),
        (
            json.dumps(_raw_row("sample_001", raw_output=_final_output(_valid_payload())))
            + "\n"
            + json.dumps(
                _raw_row(
                    "sample_002",
                    raw_output=_final_output(_valid_payload()),
                    run_id="run_002",
                )
            )
            + "\n"
        ),
    ],
)
def test_parse_reasoner_artifact_rejects_corrupt_source(
    tmp_path: Path,
    content: str,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    raw_path.write_text(content, encoding="utf-8")

    with pytest.raises(ParseError):
        parse_reasoner_artifact(raw_path)

    assert not (tmp_path / PARSED_REASONER_FILENAME).exists()


def test_parse_reasoner_artifact_rejects_duplicate_raw_json_keys(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    raw_path.write_text(
        '{"run_id":"run_001","sample_id":"sample_001","sample_id":"sample_002",'
        '"status":"generated","raw_output":"x"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ParseError, match="duplicate key"):
        parse_reasoner_artifact(raw_path)


def test_parse_reasoner_artifact_rejects_incompatible_raw_output_state(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    _write_jsonl(
        raw_path,
        [_raw_row("sample_001", raw_output=_final_output(_valid_payload()), status="image_failed")],
    )

    with pytest.raises(ParseError, match="raw_output"):
        parse_reasoner_artifact(raw_path)


def test_parse_reasoner_artifact_validates_expected_run_and_ordered_sample_set(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    _write_jsonl(
        raw_path,
        [
            _raw_row("sample_001", raw_output=_final_output(_valid_payload())),
            _raw_row("sample_002", raw_output=_final_output(_valid_payload())),
        ],
    )

    with pytest.raises(ParseError, match="expected run_id"):
        parse_reasoner_artifact(raw_path, expected_run_id="run_other")
    with pytest.raises(ParseError, match="ordered sample IDs"):
        parse_reasoner_artifact(
            raw_path,
            expected_run_id="run_001",
            expected_sample_ids=("sample_001",),
        )
    with pytest.raises(ParseError, match="ordered sample IDs"):
        parse_reasoner_artifact(
            raw_path,
            expected_run_id="run_001",
            expected_sample_ids=("sample_002", "sample_001"),
        )

    assert not (tmp_path / PARSED_REASONER_FILENAME).exists()


def test_parse_reasoner_artifact_wraps_source_read_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    _write_jsonl(raw_path, [_raw_row("sample_001", raw_output=_final_output(_valid_payload()))])
    original_read_text = Path.read_text

    def fail_raw_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == raw_path:
            raise OSError("injected unreadable source")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_raw_read)

    with pytest.raises(ParseError, match="injected unreadable source"):
        parse_reasoner_artifact(raw_path)


def test_parse_reasoner_artifact_does_not_overwrite_existing_output(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    parsed_path = tmp_path / PARSED_REASONER_FILENAME
    _write_jsonl(raw_path, [_raw_row("sample_001", raw_output=_final_output(_valid_payload()))])
    parsed_path.write_text("existing completed output", encoding="utf-8")

    with pytest.raises(ParseError, match="already exists"):
        parse_reasoner_artifact(raw_path)

    assert parsed_path.read_text(encoding="utf-8") == "existing completed output"


def test_parse_reasoner_artifact_does_not_clobber_concurrent_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    parsed_path = tmp_path / PARSED_REASONER_FILENAME
    _write_jsonl(raw_path, [_raw_row("sample_001", raw_output=_final_output(_valid_payload()))])

    import multimodal_bias.parsing as parsing

    real_link = parsing.os.link

    def create_destination_before_link(source: Path, destination: Path) -> None:
        Path(destination).write_text("concurrent completed output", encoding="utf-8")
        real_link(source, destination)

    monkeypatch.setattr(parsing.os, "link", create_destination_before_link)

    with pytest.raises(ParseError, match="already exists"):
        parse_reasoner_artifact(raw_path)

    assert parsed_path.read_text(encoding="utf-8") == "concurrent completed output"
    assert list(tmp_path.glob(f".{PARSED_REASONER_FILENAME}.*.tmp")) == []


def test_parse_reasoner_artifact_cleans_temporary_file_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_path = tmp_path / "raw_reasoner.jsonl"
    _write_jsonl(
        raw_path,
        [
            _raw_row("sample_001", raw_output=_final_output(_valid_payload())),
            _raw_row("sample_002", raw_output=_final_output(_valid_payload())),
        ],
    )

    import multimodal_bias.parsing as parsing

    original_write_record = parsing._write_csv_record
    write_count = 0

    def fail_second_write(writer: csv.DictWriter, record: object, *, schema_mode: str) -> None:
        nonlocal write_count
        write_count += 1
        if write_count == 2:
            raise OSError("injected write failure")
        original_write_record(writer, record, schema_mode=schema_mode)

    monkeypatch.setattr(parsing, "_write_csv_record", fail_second_write)

    with pytest.raises(OSError, match="injected write failure"):
        parse_reasoner_artifact(raw_path)

    assert not (tmp_path / PARSED_REASONER_FILENAME).exists()
    assert list(tmp_path.glob(f".{PARSED_REASONER_FILENAME}.*.tmp")) == []


def test_parse_verifier_output_accepts_exact_contract() -> None:
    parsed = parse_verifier_output(_verifier_output(_verifier_payload()))

    assert parsed.parse_status == "valid"
    assert parsed.parse_error is None
    assert parsed.output is not None
    assert parsed.output.label == "1"
    assert parsed.output.reasoner_defect_found is True
    assert parsed.output.objective_support is True


@pytest.mark.parametrize(
    ("raw_output", "expected_status"),
    [
        ("no marker", "missing_marker"),
        ("FINAL_VERIFICATION_JSON: {bad}", "invalid_json"),
        (
            'FINAL_VERIFICATION_JSON: {"label":"0","label":"1",'
            '"reason":"x","evidence_type":"elimination",'
            '"reasoner_defect_found":true,"objective_support":true}',
            "invalid_json",
        ),
        (
            'FINAL_VERIFICATION_JSON: {"label":"0","reason":"x",'
            '"evidence_type":"elimination","reasoner_defect_found":NaN,'
            '"objective_support":true}',
            "invalid_json",
        ),
        (_verifier_output({"label": "0"}), "invalid_schema"),
        (_verifier_output(_verifier_payload(extra="x")), "invalid_schema"),
        (_verifier_output(_verifier_payload(label="3")), "invalid_label"),
        (_verifier_output(_verifier_payload(reason=" ")), "invalid_schema"),
        (_verifier_output(_verifier_payload(evidence_type="appearance")), "invalid_schema"),
        (
            _verifier_output(_verifier_payload(reasoner_defect_found="true")),
            "invalid_schema",
        ),
        (_verifier_output(_verifier_payload(objective_support=1)), "invalid_schema"),
        (_verifier_output(_verifier_payload(reason="bad \ud800")), "invalid_schema"),
    ],
)
def test_parse_verifier_output_rejects_malformed_contract(
    raw_output: str,
    expected_status: str,
) -> None:
    parsed = parse_verifier_output(raw_output)

    assert parsed.output is None
    assert parsed.parse_status == expected_status
    assert parsed.parse_error


def test_parse_verifier_output_requires_marker_on_final_non_empty_line() -> None:
    parsed = parse_verifier_output(_verifier_output(_verifier_payload()) + "\ntrailing text")

    assert parsed.output is None
    assert parsed.parse_status == "missing_marker"


def test_read_parsed_reasoner_artifact_hydrates_valid_and_invalid_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / PARSED_REASONER_FILENAME
    _write_csv(
        path,
        list(PARSED_REASONER_FIELDNAMES),
        [
            {
                "run_id": "run_001",
                "sample_id": "sample_001",
                "parsed_label": "0",
                "uncertainty_option_index": "2",
                "evidence_summary": "The context identifies the first person.",
                "evidence_type": "stated_text_fact",
                "uncertainty_signal": "false",
                "risk_flags": "[]",
                "schema_version": "reasoner_output_v3",
                "parse_status": "valid",
                "parse_error": "",
            },
            {
                "run_id": "run_001",
                "sample_id": "sample_002",
                "parsed_label": "",
                "uncertainty_option_index": "",
                "evidence_summary": "",
                "evidence_type": "",
                "uncertainty_signal": "",
                "risk_flags": '["invalid_parse"]',
                "schema_version": "",
                "parse_status": "invalid_json",
                "parse_error": "bad JSON",
            },
        ],
    )

    records = read_parsed_reasoner_artifact(
        path,
        expected_run_id="run_001",
        expected_sample_ids=("sample_001", "sample_002"),
    )

    assert [record.sample_id for record in records] == ["sample_001", "sample_002"]
    assert records[0].parsed_label == "0"
    assert records[1].parsed_label is None
    assert records[1].risk_flags == ("invalid_parse",)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("run_id", "run_other", "run_id"),
        ("evidence_summary", "   ", "evidence_summary"),
        ("uncertainty_signal", "yes", "uncertainty_signal"),
        ("risk_flags", '["invalid_parse"]', "valid state"),
        ("risk_flags", '["unknown"]', "risk_flags"),
        ("parse_status", "unknown", "parse_status"),
    ],
)
def test_read_parsed_reasoner_artifact_rejects_invalid_rows(
    tmp_path: Path,
    field: str,
    value: str,
    match: str,
) -> None:
    path = tmp_path / PARSED_REASONER_FILENAME
    row = {
        "run_id": "run_001",
        "sample_id": "sample_001",
        "parsed_label": "0",
        "uncertainty_option_index": "2",
        "evidence_summary": "Evidence",
        "evidence_type": "stated_text_fact",
        "uncertainty_signal": "false",
        "risk_flags": "[]",
        "schema_version": "reasoner_output_v3",
        "parse_status": "valid",
        "parse_error": "",
    }
    row[field] = value
    _write_csv(path, list(PARSED_REASONER_FIELDNAMES), [row])

    with pytest.raises(ParseError, match=match):
        read_parsed_reasoner_artifact(
            path,
            expected_run_id="run_001",
            expected_sample_ids=("sample_001",),
        )


def test_read_parsed_reasoner_artifact_rejects_wrong_order_and_headers(
    tmp_path: Path,
) -> None:
    path = tmp_path / PARSED_REASONER_FILENAME
    _write_csv(
        path,
        list(PARSED_REASONER_FIELDNAMES),
        [
            {
                "run_id": "run_001",
                "sample_id": "sample_001",
                "parsed_label": "0",
                "uncertainty_option_index": "2",
                "evidence_summary": "Evidence",
                "evidence_type": "stated_text_fact",
                "uncertainty_signal": "false",
                "risk_flags": "[]",
                "schema_version": "reasoner_output_v3",
                "parse_status": "valid",
                "parse_error": "",
            }
        ],
    )
    with pytest.raises(ParseError, match="ordered sample IDs"):
        read_parsed_reasoner_artifact(
            path,
            expected_run_id="run_001",
            expected_sample_ids=("sample_other",),
        )

    path.unlink()
    _write_csv(path, ["run_id", "sample_id"], [{"run_id": "run_001", "sample_id": "x"}])
    with pytest.raises(ParseError, match="headers"):
        read_parsed_reasoner_artifact(
            path,
            expected_run_id="run_001",
            expected_sample_ids=("x",),
        )


def test_read_parsed_reasoner_artifact_requires_invalid_row_parse_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / PARSED_REASONER_FILENAME
    _write_csv(
        path,
        list(PARSED_REASONER_FIELDNAMES),
        [
            {
                "run_id": "run_001",
                "sample_id": "sample_001",
                "parsed_label": "",
                "uncertainty_option_index": "",
                "evidence_summary": "",
                "evidence_type": "",
                "uncertainty_signal": "",
                "risk_flags": '["invalid_parse"]',
                "schema_version": "",
                "parse_status": "invalid_json",
                "parse_error": "",
            }
        ],
    )

    with pytest.raises(ParseError, match="requires parse_error"):
        read_parsed_reasoner_artifact(
            path,
            expected_run_id="run_001",
            expected_sample_ids=("sample_001",),
        )


def test_read_parsed_reasoner_artifact_requires_invalid_parse_flag(
    tmp_path: Path,
) -> None:
    path = tmp_path / PARSED_REASONER_FILENAME
    _write_csv(
        path,
        list(PARSED_REASONER_FIELDNAMES),
        [
            {
                "run_id": "run_001",
                "sample_id": "sample_001",
                "parsed_label": "",
                "uncertainty_option_index": "",
                "evidence_summary": "",
                "evidence_type": "",
                "uncertainty_signal": "",
                "risk_flags": "[]",
                "schema_version": "",
                "parse_status": "invalid_json",
                "parse_error": "bad JSON",
            }
        ],
    )

    with pytest.raises(ParseError, match="invalid_parse"):
        read_parsed_reasoner_artifact(
            path,
            expected_run_id="run_001",
            expected_sample_ids=("sample_001",),
        )
