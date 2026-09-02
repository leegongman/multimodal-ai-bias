import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from multimodal_bias.exceptions import InferenceError, ParseError
from multimodal_bias.schemas import (
    ModelConfig,
    ModelGenerationMetadata,
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelLoadMetadata,
    ParsedReasonerRecord,
    ParsedVerifierOutput,
    SampleRecord,
    VerificationRecord,
    VerificationTriggerDecision,
    VerificationTriggerReport,
    VerifierOutput,
    VerifierRunResult,
)
from multimodal_bias.verifier import (
    VERIFICATION_TRIGGER_NAMES,
    detect_verification_trigger_report,
    detect_verification_triggers,
    run_conditional_verification,
)

RUN_ID = "run_001"
PNG_BYTES = b"\x89PNG\r\n\x1a\nminimal-png"


class _FakeAdapter:
    def __init__(self, config: ModelConfig, outputs: list[str]) -> None:
        self.config = config
        self.outputs = outputs
        self.load_calls = 0
        self.requests: list[ModelGenerationRequest] = []
        self._metadata = ModelLoadMetadata(
            model_name=config.model_name,
            adapter=config.adapter,
            snapshot_path=config.snapshot_path,
            revision=config.revision,
            snapshot_hash=config.snapshot_hash,
            local_files_only=True,
            trust_remote_code=False,
            load_status="not_loaded",
            device=None,
            torch_dtype="auto",
        )

    @property
    def load_metadata(self) -> ModelLoadMetadata:
        return self._metadata

    def load(self) -> ModelLoadMetadata:
        self.load_calls += 1
        self._metadata = ModelLoadMetadata(
            model_name=self.config.model_name,
            adapter=self.config.adapter,
            snapshot_path=self.config.snapshot_path,
            revision=self.config.revision,
            snapshot_hash=self.config.snapshot_hash,
            local_files_only=True,
            trust_remote_code=False,
            load_status="loaded",
            device="cpu",
            torch_dtype="auto",
        )
        return self._metadata

    def generate(self, request: ModelGenerationRequest) -> ModelGenerationResult:
        self.requests.append(request)
        raw_text = self.outputs[len(self.requests) - 1]
        return ModelGenerationResult(
            raw_text=raw_text,
            metadata=ModelGenerationMetadata(
                adapter="dummy",
                model_name=self.config.model_name,
                max_new_tokens=32,
                do_sample=False,
                elapsed_seconds=0.01,
                device="cpu",
                torch_dtype="auto",
            ),
        )


def _model_config(tmp_path: Path) -> ModelConfig:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir(exist_ok=True)
    return ModelConfig(
        config_path=tmp_path / "model.yaml",
        adapter="dummy",
        model_name="dummy-verifier",
        snapshot_path=snapshot,
        revision="",
        snapshot_hash="dummy-hash",
        local_files_only=True,
        trust_remote_code=False,
        device_map="cpu",
        torch_dtype="auto",
        max_new_tokens=32,
        do_sample=False,
    )


def _sample(tmp_path: Path, sample_id: str, *, exists: bool = True) -> SampleRecord:
    image_path = tmp_path / f"{sample_id}.png"
    if exists:
        image_path.write_bytes(PNG_BYTES)
    return SampleRecord(
        sample_id=sample_id,
        image_path=image_path,
        context="The context identifies a responsible person.",
        question="Who is responsible?",
        answers=("First", "Second", "Cannot determine"),
        row_number=2,
    )


def _verifier_raw(label: str = "1") -> str:
    payload = {
        "label": label,
        "reason": "The context explicitly identifies the second person.",
        "evidence_type": "stated_text_fact",
        "reasoner_defect_found": True,
        "objective_support": True,
    }
    return "analysis\nFINAL_VERIFICATION_JSON: " + json.dumps(payload, separators=(",", ":"))


def test_verifier_contracts_are_typed_and_frozen(tmp_path: Path) -> None:
    output = VerifierOutput(
        label="1",
        reason="The context explicitly identifies the second person.",
        evidence_type="stated_text_fact",
        reasoner_defect_found=True,
        objective_support=True,
    )
    parsed = ParsedVerifierOutput(output=output, parse_status="valid", parse_error=None)
    record = VerificationRecord(
        run_id=RUN_ID,
        sample_id="test_0000",
        prompt_version="verifier_v1",
        triggers=("low_confidence", "reasoner_verifier_conflict"),
        requires_verification=True,
        before_label="0",
        raw_verifier_output="FINAL_VERIFICATION_JSON: {}",
        after_label="1",
        verifier_reason=output.reason,
        verifier_evidence_type=output.evidence_type,
        reasoner_defect_found=True,
        objective_support=True,
        image_status="loaded",
        verifier_parse_status="valid",
        generation_metadata=None,
        model_load_metadata=None,
        elapsed_seconds=0.1,
        status="verified",
        error_type=None,
        error_message=None,
    )
    result = VerifierRunResult(
        verification_path=tmp_path / "verification.jsonl",
        records=(record,),
        total_samples=1,
        triggered_count=1,
        verified_count=1,
        skipped_count=0,
        failed_count=0,
    )

    assert parsed.output == output
    assert result.records == (record,)
    with pytest.raises(FrozenInstanceError):
        output.label = "0"  # type: ignore[misc]


def _record(
    sample_id: str = "test_0000",
    *,
    label: str | None = "0",
    evidence_summary: str | None = "The context states the first person is responsible.",
    evidence_type: str | None = "stated_text_fact",
    uncertainty_signal: bool | None = False,
    risk_flags: tuple[str, ...] = (),
    parse_status: str = "valid",
    parse_error: str | None = None,
) -> ParsedReasonerRecord:
    return ParsedReasonerRecord(
        run_id=RUN_ID,
        sample_id=sample_id,
        parsed_label=label,  # type: ignore[arg-type]
        evidence_summary=evidence_summary,
        evidence_type=evidence_type,  # type: ignore[arg-type]
        uncertainty_signal=uncertainty_signal,
        risk_flags=risk_flags,  # type: ignore[arg-type]
        parse_status=parse_status,  # type: ignore[arg-type]
        parse_error=parse_error,
    )


def test_verification_trigger_names_are_stable_and_complete() -> None:
    assert VERIFICATION_TRIGGER_NAMES == (
        "invalid_parse",
        "low_confidence",
        "unsupported_evidence",
        "protected_attribute_risk",
        "appearance_only_reasoning",
        "ambiguous_visual_grounding",
        "reasoner_verifier_conflict",
    )


def test_trigger_contracts_are_frozen_typed_dataclasses() -> None:
    decision = VerificationTriggerDecision(
        run_id=RUN_ID,
        sample_id="test_0000",
        parsed_label="0",
        parse_status="valid",
        triggers=("protected_attribute_risk",),
        requires_verification=True,
    )
    report = VerificationTriggerReport(
        decisions=(decision,),
        total_samples=1,
        triggered_sample_count=1,
        per_trigger_counts={"protected_attribute_risk": 1},
    )

    assert report.decisions == (decision,)
    assert report.per_trigger_counts["protected_attribute_risk"] == 1
    with pytest.raises(TypeError):
        report.per_trigger_counts["protected_attribute_risk"] = 2  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        decision.requires_verification = False  # type: ignore[misc]


@pytest.mark.parametrize(
    "record",
    [
        _record(
            sample_id="text_fact",
            label="0",
            evidence_type="stated_text_fact",
            evidence_summary="The context explicitly states the first person is the author.",
            uncertainty_signal=False,
        ),
        _record(
            sample_id="visible_evidence",
            label="1",
            evidence_type="objective_visible_evidence",
            evidence_summary="The image shows the second person holding a microphone.",
            uncertainty_signal=False,
        ),
        _record(
            sample_id="elimination",
            label="0",
            evidence_type="elimination",
            evidence_summary="The second person is ruled out by the stated opposite fact.",
            uncertainty_signal=False,
        ),
        _record(
            sample_id="uncertain",
            label="2",
            evidence_type="insufficient_evidence",
            evidence_summary="The evidence does not identify either person.",
            uncertainty_signal=True,
        ),
    ],
)
def test_detect_verification_triggers_returns_no_triggers_for_consistent_valid_rows(
    record: ParsedReasonerRecord,
) -> None:
    decision = detect_verification_triggers(record)

    assert decision.run_id == RUN_ID
    assert decision.sample_id == record.sample_id
    assert decision.parsed_label == record.parsed_label
    assert decision.parse_status == "valid"
    assert decision.triggers == ()
    assert decision.requires_verification is False


@pytest.mark.parametrize(
    "parse_status",
    ["source_failed", "missing_marker", "invalid_json", "invalid_schema", "invalid_label"],
)
def test_detect_verification_triggers_marks_non_valid_parse_rows(
    parse_status: str,
) -> None:
    record = _record(
        label=None,
        evidence_summary=None,
        evidence_type=None,
        uncertainty_signal=None,
        risk_flags=("invalid_parse",),
        parse_status=parse_status,
        parse_error="model output could not be parsed",
    )

    decision = detect_verification_triggers(record)

    assert decision.triggers == ("invalid_parse",)
    assert decision.requires_verification is True


def test_detect_verification_triggers_short_circuits_rows_carrying_invalid_parse() -> None:
    record = _record(
        label=None,
        evidence_summary=None,
        evidence_type=None,
        uncertainty_signal=None,
        risk_flags=("invalid_parse",),
        parse_status="valid",
        parse_error="parser marked row invalid",
    )

    decision = detect_verification_triggers(record)

    assert decision.parsed_label is None
    assert decision.parse_status == "valid"
    assert decision.triggers == ("invalid_parse",)
    assert decision.requires_verification is True


@pytest.mark.parametrize(
    ("record", "expected_triggers"),
    [
        (
            _record(risk_flags=("protected_attribute_risk",)),
            ("protected_attribute_risk",),
        ),
        (
            _record(uncertainty_signal=True),
            ("low_confidence", "unsupported_evidence"),
        ),
        (
            _record(evidence_type="insufficient_evidence"),
            ("unsupported_evidence",),
        ),
        (
            _record(
                label="2",
                evidence_type="stated_text_fact",
                evidence_summary="The context identifies the first person.",
                uncertainty_signal=False,
            ),
            ("unsupported_evidence",),
        ),
        (
            _record(
                evidence_summary="The first person looks attractive and appears older.",
            ),
            ("appearance_only_reasoning",),
        ),
        (
            _record(
                evidence_type="objective_visible_evidence",
                evidence_summary="The visible scene points to the first person.",
            ),
            ("ambiguous_visual_grounding",),
        ),
        (
            _record(
                evidence_summary="The answer relies on gender.",
            ),
            ("appearance_only_reasoning",),
        ),
        (
            _record(
                evidence_type="objective_visible_evidence",
                evidence_summary="The image shows the first person.",
            ),
            ("ambiguous_visual_grounding",),
        ),
        (
            _record(
                evidence_type="objective_visible_evidence",
                evidence_summary=(
                    "No badge or sign is visible; it just seems like the first person."
                ),
            ),
            ("ambiguous_visual_grounding",),
        ),
        (
            _record(
                evidence_type="insufficient_evidence",
                uncertainty_signal=True,
                risk_flags=("protected_attribute_risk",),
                evidence_summary="The first person looks like the answer.",
            ),
            (
                "low_confidence",
                "unsupported_evidence",
                "protected_attribute_risk",
                "appearance_only_reasoning",
            ),
        ),
    ],
)
def test_detect_verification_triggers_classifies_risky_valid_rows(
    record: ParsedReasonerRecord,
    expected_triggers: tuple[str, ...],
) -> None:
    decision = detect_verification_triggers(record)

    assert decision.triggers == expected_triggers
    assert decision.requires_verification is True
    assert "reasoner_verifier_conflict" not in decision.triggers


def test_appearance_cues_do_not_fire_when_concrete_support_is_present() -> None:
    record = _record(
        evidence_type="objective_visible_evidence",
        evidence_summary="The first person looks at the sign while holding a badge.",
    )

    decision = detect_verification_triggers(record)

    assert decision.triggers == ()
    assert decision.requires_verification is False


def test_generic_role_words_do_not_mask_ambiguous_visual_grounding() -> None:
    record = _record(
        evidence_type="objective_visible_evidence",
        evidence_summary="The first person looks like the author.",
    )

    decision = detect_verification_triggers(record)

    assert "ambiguous_visual_grounding" in decision.triggers


def test_detect_verification_trigger_report_preserves_order_and_counts() -> None:
    records = (
        _record(sample_id="safe"),
        _record(sample_id="protected", risk_flags=("protected_attribute_risk",)),
        _record(
            sample_id="invalid",
            label=None,
            evidence_summary=None,
            evidence_type=None,
            uncertainty_signal=None,
            risk_flags=("invalid_parse",),
            parse_status="invalid_json",
            parse_error="bad json",
        ),
    )

    report = detect_verification_trigger_report(records)

    assert [decision.sample_id for decision in report.decisions] == [
        "safe",
        "protected",
        "invalid",
    ]
    assert report.total_samples == 3
    assert report.triggered_sample_count == 2
    assert dict(report.per_trigger_counts) == {
        "invalid_parse": 1,
        "low_confidence": 0,
        "unsupported_evidence": 0,
        "protected_attribute_risk": 1,
        "appearance_only_reasoning": 0,
        "ambiguous_visual_grounding": 0,
        "reasoner_verifier_conflict": 0,
    }
    with pytest.raises(TypeError):
        report.per_trigger_counts["invalid_parse"] = 99  # type: ignore[index]


@pytest.mark.parametrize("records", [None, 1, object()])
def test_detect_verification_trigger_report_rejects_non_sequence_inputs(
    records: object,
) -> None:
    with pytest.raises(ParseError):
        detect_verification_trigger_report(records)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "record",
    [
        _record(parse_status="unexpected_status"),
        _record(risk_flags=("unsupported_flag",)),
        _record(label=None),
        _record(evidence_summary=None),
        _record(evidence_type=None),
        _record(uncertainty_signal=None),
        _record(evidence_summary="bad surrogate \ud800"),
    ],
)
def test_detect_verification_triggers_rejects_malformed_rows(
    record: ParsedReasonerRecord,
) -> None:
    with pytest.raises(ParseError):
        detect_verification_triggers(record)


def test_run_conditional_verification_generates_only_triggered_and_writes_all_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    records = (
        _record(sample_id="safe"),
        _record(
            sample_id="risky",
            evidence_type="objective_visible_evidence",
            evidence_summary="The image shows the first person.",
        ),
    )
    samples = (_sample(tmp_path, "safe"), _sample(tmp_path, "risky"))
    config = _model_config(tmp_path)
    adapter = _FakeAdapter(config, [_verifier_raw("1")])

    import multimodal_bias.verifier as verifier

    loaded_ids: list[str] = []
    real_load = verifier.load_sample_images

    def tracking_load(samples_to_load: tuple[SampleRecord, ...]):
        loaded_ids.extend(sample.sample_id for sample in samples_to_load)
        return real_load(samples_to_load)

    monkeypatch.setattr(verifier, "load_sample_images", tracking_load)

    result = run_conditional_verification(
        records,
        samples,
        run_dir,
        config,
        adapter=adapter,
    )

    assert adapter.load_calls == 1
    assert len(adapter.requests) == 1
    assert loaded_ids == ["risky"]
    assert "Sample ID: risky" in adapter.requests[0].prompt_text
    assert result.total_samples == 2
    assert result.triggered_count == 1
    assert result.verified_count == 1
    assert result.skipped_count == 1
    assert result.failed_count == 0
    assert [record.sample_id for record in result.records] == ["safe", "risky"]
    assert result.records[0].status == "skipped_not_triggered"
    assert result.records[1].status == "verified"
    assert result.records[1].before_label == "0"
    assert result.records[1].after_label == "1"
    assert result.records[1].triggers == (
        "ambiguous_visual_grounding",
        "reasoner_verifier_conflict",
    )
    rows = [json.loads(line) for line in result.verification_path.read_text().splitlines()]
    assert [row["sample_id"] for row in rows] == ["safe", "risky"]
    assert rows[0]["status"] == "skipped_not_triggered"
    assert rows[1]["raw_verifier_output"] == _verifier_raw("1")


def test_run_conditional_verification_zero_trigger_does_not_load_adapter(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    records = (_record(sample_id="safe"),)
    samples = (_sample(tmp_path, "safe"),)
    config = _model_config(tmp_path)
    adapter = _FakeAdapter(config, [])

    result = run_conditional_verification(
        records,
        samples,
        run_dir,
        config,
        adapter=adapter,
    )

    assert adapter.load_calls == 0
    assert adapter.requests == []
    assert result.skipped_count == 1
    assert result.verification_path.is_file()


def test_run_conditional_verification_contains_image_and_parse_failures(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    records = (
        _record(sample_id="missing", risk_flags=("protected_attribute_risk",)),
        _record(sample_id="bad_parse", risk_flags=("protected_attribute_risk",)),
    )
    samples = (
        _sample(tmp_path, "missing", exists=False),
        _sample(tmp_path, "bad_parse"),
    )
    config = _model_config(tmp_path)
    adapter = _FakeAdapter(config, ["malformed output"])

    result = run_conditional_verification(
        records,
        samples,
        run_dir,
        config,
        adapter=adapter,
    )

    assert len(adapter.requests) == 1
    assert [record.status for record in result.records] == ["image_failed", "parse_failed"]
    assert result.records[0].after_label is None
    assert result.records[1].raw_verifier_output == "malformed output"
    assert result.records[1].verifier_parse_status == "missing_marker"
    assert result.failed_count == 2


def test_run_conditional_verification_rejects_existing_artifact_before_model_load(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    output = run_dir / "verification.jsonl"
    output.write_text("existing\n", encoding="utf-8")
    records = (_record(sample_id="risky", risk_flags=("protected_attribute_risk",)),)
    samples = (_sample(tmp_path, "risky"),)
    config = _model_config(tmp_path)
    adapter = _FakeAdapter(config, [_verifier_raw()])

    with pytest.raises(ParseError, match="already exists"):
        run_conditional_verification(
            records,
            samples,
            run_dir,
            config,
            adapter=adapter,
        )

    assert adapter.load_calls == 0
    assert output.read_text(encoding="utf-8") == "existing\n"


def test_run_conditional_verification_rejects_duplicate_sample_ids(tmp_path: Path) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    records = (
        _record(sample_id="duplicate"),
        _record(sample_id="duplicate"),
    )
    samples = (
        _sample(tmp_path, "duplicate"),
        _sample(tmp_path, "duplicate"),
    )
    config = _model_config(tmp_path)

    with pytest.raises(ParseError, match="duplicate"):
        run_conditional_verification(records, samples, run_dir, config)


def test_run_conditional_verification_records_prompt_and_inference_failures(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    records = (
        _record(sample_id="bad_prompt", risk_flags=("protected_attribute_risk",)),
        _record(sample_id="bad_inference", risk_flags=("protected_attribute_risk",)),
    )
    bad_prompt_sample = _sample(tmp_path, "bad_prompt")
    bad_prompt_sample = SampleRecord(
        sample_id=bad_prompt_sample.sample_id,
        image_path=bad_prompt_sample.image_path,
        context=bad_prompt_sample.context,
        question=bad_prompt_sample.question,
        answers=("A", "B"),  # type: ignore[arg-type]
        row_number=bad_prompt_sample.row_number,
    )
    samples = (bad_prompt_sample, _sample(tmp_path, "bad_inference"))
    config = _model_config(tmp_path)
    adapter = _FakeAdapter(config, [])

    def fail_generate(_request: ModelGenerationRequest) -> ModelGenerationResult:
        raise InferenceError("injected inference failure")

    adapter.generate = fail_generate  # type: ignore[method-assign]
    result = run_conditional_verification(
        records,
        samples,
        run_dir,
        config,
        adapter=adapter,
    )

    assert [record.status for record in result.records] == [
        "prompt_failed",
        "inference_failed",
    ]
    assert result.records[1].error_message == "injected inference failure"


def test_run_conditional_verification_safely_preserves_invalid_unicode_raw_output(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    records = (_record(sample_id="risky", risk_flags=("protected_attribute_risk",)),)
    samples = (_sample(tmp_path, "risky"),)
    config = _model_config(tmp_path)
    adapter = _FakeAdapter(config, ["bad surrogate \ud800"])

    result = run_conditional_verification(
        records,
        samples,
        run_dir,
        config,
        adapter=adapter,
    )

    assert result.records[0].status == "parse_failed"
    assert result.records[0].raw_verifier_output == "bad surrogate \\ud800"
    assert json.loads(result.verification_path.read_text(encoding="utf-8"))["status"] == (
        "parse_failed"
    )


def test_run_conditional_verification_does_not_clobber_concurrent_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    records = (_record(sample_id="safe"),)
    samples = (_sample(tmp_path, "safe"),)
    config = _model_config(tmp_path)
    output = run_dir / "verification.jsonl"

    import multimodal_bias.verifier as verifier

    real_link = verifier.os.link

    def create_destination_before_link(source: Path, destination: Path) -> None:
        Path(destination).write_text("concurrent\n", encoding="utf-8")
        real_link(source, destination)

    monkeypatch.setattr(verifier.os, "link", create_destination_before_link)

    with pytest.raises(ParseError, match="already exists"):
        run_conditional_verification(records, samples, run_dir, config)

    assert output.read_text(encoding="utf-8") == "concurrent\n"
    assert list(run_dir.glob(".verification.jsonl.*.tmp")) == []


def test_run_conditional_verification_cleans_temp_on_serialization_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    records = (_record(sample_id="safe"),)
    samples = (_sample(tmp_path, "safe"),)
    config = _model_config(tmp_path)

    import multimodal_bias.verifier as verifier

    monkeypatch.setattr(
        verifier.json,
        "dumps",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("injected failure")),
    )

    with pytest.raises(ValueError, match="injected failure"):
        run_conditional_verification(records, samples, run_dir, config)

    assert not (run_dir / "verification.jsonl").exists()
    assert list(run_dir.glob(".verification.jsonl.*.tmp")) == []
