from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_runner() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts" / "run_gemma4_12b_v3_vllm.py"
    spec = importlib.util.spec_from_file_location("gemma4_v3_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner()


def valid_json(label: str = "0", uncertainty_index: int = 1) -> str:
    return (
        "{"
        f'"label":"{label}",'
        f'"uncertainty_option_index":{uncertainty_index},'
        '"evidence":"The stated context identifies the supported option.",'
        '"evidence_type":"stated_text_fact",'
        '"uncertainty_signal":false,'
        '"protected_attribute_risk":false,'
        '"schema_version":"reasoner_output_v3"'
        "}"
    )


def record(sample_id: str, raw_output: str | None, *, attempt: int = 1) -> dict:
    return {
        "run_id": "run",
        "sample_id": sample_id,
        "attempt": attempt,
        "status": "generated" if raw_output is not None else "inference_failed",
        "raw_output": raw_output,
        "error_message": None if raw_output is not None else "failed",
    }


def test_runner_is_pinned_to_official_gemma4_12b() -> None:
    assert RUNNER.MODEL_NAME == "google/gemma-4-12B-it"
    assert RUNNER.DEFAULT_INITIAL_MAX_TOKENS == 256
    assert RUNNER.DEFAULT_RETRY_MAX_TOKENS == 512


def test_schema_enumerates_nine_semantic_variants_and_bounds_evidence() -> None:
    variants = RUNNER.REASONER_V3_SEMANTIC_VARIANTS
    assert len(variants) == 9
    for variant in variants:
        evidence = variant["properties"]["evidence"]
        assert evidence == {
            "type": "string",
            "minLength": 1,
            "maxLength": RUNNER.MAX_EVIDENCE_CHARACTERS,
        }
        label = int(variant["properties"]["label"]["const"])
        uncertainty = variant["properties"]["uncertainty_option_index"]["const"]
        if label == uncertainty:
            assert variant["properties"]["uncertainty_signal"]["const"] is True
            assert (
                variant["properties"]["evidence_type"]["const"]
                == "insufficient_evidence"
            )
        else:
            assert variant["properties"]["uncertainty_signal"]["const"] is False


def test_normalizer_extracts_json_from_gemma_channel_wrappers() -> None:
    wrapped = (
        "<|channel|>thought\n<|channel|>final\n"
        + valid_json()
        + "<|end_of_turn|>"
    )
    normalized = RUNNER.normalize_v3_final_line(wrapped)
    assert normalized.startswith("FINAL_ANSWER_JSON:")
    assert RUNNER.extract_json_object(normalized)["label"] == "0"


def test_valid_record_is_not_retried() -> None:
    valid = record("TEST_0000", RUNNER.normalize_v3_final_line(valid_json()))
    assert RUNNER.should_retry(valid) is False


def test_truncated_and_failed_records_are_retried() -> None:
    truncated = record("TEST_0000", '{"label":"0","evidence":"unfinished')
    failed = record("TEST_0001", None)
    assert RUNNER.should_retry(truncated) is True
    assert RUNNER.should_retry(failed) is True


def test_retry_replaces_only_its_matching_sample() -> None:
    first = record("TEST_0000", RUNNER.normalize_v3_final_line(valid_json()))
    invalid = record("TEST_0001", "truncated")
    retry = record(
        "TEST_0001",
        RUNNER.normalize_v3_final_line(valid_json(label="2", uncertainty_index=1)),
        attempt=2,
    )
    selected = RUNNER.choose_final_records(
        [first, invalid], {retry["sample_id"]: retry}
    )
    assert selected == [first, retry]
    assert selected[0]["attempt"] == 1
    assert selected[1]["attempt"] == 2


def test_submission_requires_every_full_run_row_to_be_valid() -> None:
    assert RUNNER.should_publish_submission(8_500, 8_500) is True
    assert RUNNER.should_publish_submission(8_500, 8_499) is False
    assert RUNNER.should_publish_submission(50, 50) is False
