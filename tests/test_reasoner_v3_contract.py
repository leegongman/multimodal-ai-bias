import json

import pytest

from multimodal_bias.exceptions import ParseError
from multimodal_bias.parsing import parse_reasoner_output
from multimodal_bias.prompting.guards import REASONER_OUTPUT_SCHEMA_VERSION
from multimodal_bias.prompting.templates import load_reasoner_prompt_template


def _raw(**overrides: object) -> str:
    payload: dict[str, object] = {
        "label": "2",
        "uncertainty_option_index": 2,
        "evidence": "The available evidence does not determine an answer.",
        "evidence_type": "insufficient_evidence",
        "uncertainty_signal": True,
        "protected_attribute_risk": False,
        "schema_version": REASONER_OUTPUT_SCHEMA_VERSION,
    }
    payload.update(overrides)
    return "FINAL_ANSWER_JSON:" + json.dumps(payload, separators=(",", ":"))


@pytest.mark.parametrize("index", [0, 1, 2])
def test_v3_accepts_uncertainty_at_every_option_index(index: int) -> None:
    record = parse_reasoner_output(
        _raw(label=str(index), uncertainty_option_index=index),
        run_id="run_001",
        sample_id=f"sample_{index}",
    )

    assert record.parse_status == "valid"
    assert record.parsed_label == str(index)
    assert record.uncertainty_option_index == index
    assert record.schema_version == REASONER_OUTPUT_SCHEMA_VERSION


def test_v3_accepts_decisive_selection_separate_from_uncertainty() -> None:
    record = parse_reasoner_output(
        _raw(
            label="0",
            uncertainty_option_index=2,
            evidence_type="objective_visible_evidence",
            uncertainty_signal=False,
        ),
        run_id="run_001",
        sample_id="sample_decisive",
    )

    assert record.parse_status == "valid"


@pytest.mark.parametrize(
    "overrides",
    [
        {"schema_version": "reasoner_output_v2"},
        {"uncertainty_option_index": "2"},
        {"uncertainty_option_index": 3},
        {"label": "2", "uncertainty_option_index": 2, "uncertainty_signal": False},
        {"label": "0", "uncertainty_option_index": 2, "uncertainty_signal": True},
        {
            "label": "0",
            "uncertainty_option_index": 2,
            "uncertainty_signal": False,
            "evidence_type": "insufficient_evidence",
        },
    ],
)
def test_v3_rejects_schema_and_semantic_mismatches(overrides: dict[str, object]) -> None:
    record = parse_reasoner_output(_raw(**overrides), run_id="run_001", sample_id="sample_invalid")

    assert record.parse_status == "invalid_schema"
    assert record.parsed_label is None
    assert record.uncertainty_option_index is None
    assert record.schema_version is None


def test_v3_is_default_and_v2_remains_explicitly_loadable() -> None:
    assert load_reasoner_prompt_template().version == "reasoner_v3"
    assert (
        load_reasoner_prompt_template("configs/prompts/reasoner_v2.yaml").version == "reasoner_v2"
    )


def test_v2_output_is_accepted_only_in_explicit_v2_mode() -> None:
    payload = {
        "label": "2",
        "evidence": "The evidence is insufficient.",
        "evidence_type": "insufficient_evidence",
        "uncertainty_signal": True,
        "protected_attribute_risk": False,
    }
    raw = "FINAL_ANSWER_JSON:" + json.dumps(payload, separators=(",", ":"))

    default_record = parse_reasoner_output(raw, run_id="run", sample_id="sample")
    explicit_v2_record = parse_reasoner_output(
        raw, run_id="run", sample_id="sample", schema_mode="v2"
    )

    assert default_record.parse_status == "invalid_schema"
    assert explicit_v2_record.parse_status == "valid"
    assert explicit_v2_record.schema_version is None
    assert explicit_v2_record.uncertainty_option_index is None


def test_invalid_schema_mode_is_rejected_before_output_parsing() -> None:
    with pytest.raises(ParseError, match="schema_mode"):
        parse_reasoner_output("no marker", run_id="run", sample_id="sample", schema_mode="bogus")
