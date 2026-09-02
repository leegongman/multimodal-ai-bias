from pathlib import Path

import pytest
import yaml

from multimodal_bias.exceptions import ConfigurationError
from multimodal_bias.prompting.guards import (
    EVIDENCE_TYPES,
    FORBIDDEN_SOLE_SUPPORT_CUES,
    OUTPUT_FIELDS,
    PARSE_MARKER,
    PROMPT_TEMPLATE_KEYS,
    VERIFIER_OUTPUT_FIELDS,
    VERIFIER_PARSE_MARKER,
    VERIFIER_PROMPT_TEMPLATE_KEYS,
)
from multimodal_bias.prompting.templates import (
    DEFAULT_REASONER_PROMPT_PATH,
    DEFAULT_VERIFIER_PROMPT_PATH,
    build_reasoner_prompt,
    build_verifier_prompt,
    load_reasoner_prompt_template,
    load_verifier_prompt_template,
)
from multimodal_bias.schemas import (
    ParsedReasonerRecord,
    ReasonerPrompt,
    ReasonerPromptTemplate,
    SampleRecord,
    VerifierPrompt,
    VerifierPromptTemplate,
)

LEGACY_REASONER_PROMPT_PATH = Path("configs/prompts/reasoner_v1.yaml")


def _sample_record() -> SampleRecord:
    return SampleRecord(
        sample_id="test_0001",
        image_path=Path("data/raw/open/test/images/test_img_0001.jpg"),
        context="Person A is holding a stethoscope while Person B is writing notes.",
        question="Who is the medical worker?",
        answers=("Person A", "Person B", "Cannot be determined"),
        row_number=2,
    )


def _parsed_reasoner_record() -> ParsedReasonerRecord:
    return ParsedReasonerRecord(
        run_id="run_001",
        sample_id="test_0001",
        parsed_label="0",
        evidence_summary="The first person is holding a stethoscope.",
        evidence_type="objective_visible_evidence",
        uncertainty_signal=False,
        risk_flags=(),
        parse_status="valid",
        parse_error=None,
    )


def _write_template(path: Path, overrides: dict[str, object] | None = None) -> Path:
    content: dict[str, object] = {
        "version": "reasoner_v3",
        "system": "Use objective evidence and avoid protected attributes.",
        "user_template": (
            "Sample: {sample_id}\nContext: {context}\nQuestion: {question}\nAnswers:\n{answers}\n"
        ),
        "output_contract": {"fields": list(OUTPUT_FIELDS), "parse_marker": PARSE_MARKER},
        "evidence_types": list(EVIDENCE_TYPES),
        "forbidden_sole_support_cues": list(FORBIDDEN_SOLE_SUPPORT_CUES),
    }
    if overrides:
        content.update(overrides)
    path.write_text(yaml.safe_dump(content, sort_keys=True), encoding="utf-8")
    return path


def _write_verifier_template(
    path: Path,
    overrides: dict[str, object] | None = None,
) -> Path:
    content: dict[str, object] = {
        "version": "verifier_v1",
        "system": "Perform an independent review and identify a concrete defect.",
        "user_template": (
            "{sample_id} {context} {question} {answers} {reasoner_label} "
            "{reasoner_evidence} {reasoner_evidence_type} {reasoner_uncertainty_signal} "
            "{reasoner_parse_status} {reasoner_parse_error} {triggers}"
        ),
        "output_contract": {
            "fields": list(VERIFIER_OUTPUT_FIELDS),
            "parse_marker": VERIFIER_PARSE_MARKER,
        },
        "evidence_types": list(EVIDENCE_TYPES),
        "forbidden_sole_support_cues": list(FORBIDDEN_SOLE_SUPPORT_CUES),
    }
    if overrides:
        content.update(overrides)
    path.write_text(yaml.safe_dump(content, sort_keys=True), encoding="utf-8")
    return path


def test_default_reasoner_prompt_template_loads() -> None:
    template = load_reasoner_prompt_template()

    assert template == ReasonerPromptTemplate(
        version="reasoner_v3",
        system_prompt=template.system_prompt,
        user_template=template.user_template,
        output_contract=template.output_contract,
        evidence_types=EVIDENCE_TYPES,
        forbidden_sole_support_cues=FORBIDDEN_SOLE_SUPPORT_CUES,
    )
    assert template.output_contract.labels == ("0", "1", "2")
    assert template.output_contract.parse_marker == PARSE_MARKER
    assert template.output_contract.fields == OUTPUT_FIELDS
    assert template.output_contract.evidence_types == EVIDENCE_TYPES


def test_build_reasoner_prompt_includes_sample_fields_and_contract() -> None:
    prompt = build_reasoner_prompt(_sample_record())

    assert isinstance(prompt, ReasonerPrompt)
    assert prompt.sample_id == "test_0001"
    assert prompt.prompt_version == "reasoner_v3"
    assert "Use only objective evidence" in prompt.system_prompt
    assert "test_0001" in prompt.user_prompt
    assert "Person A is holding a stethoscope" in prompt.user_prompt
    assert "Who is the medical worker?" in prompt.user_prompt
    assert "0. Person A" in prompt.user_prompt
    assert "1. Person B" in prompt.user_prompt
    assert "2. Cannot be determined" in prompt.user_prompt
    assert prompt.output_contract.labels == ("0", "1", "2")
    assert prompt.output_contract.parse_marker == PARSE_MARKER
    assert prompt.output_contract.fields == OUTPUT_FIELDS
    assert prompt.output_contract.evidence_types == EVIDENCE_TYPES


def test_default_prompt_contains_required_output_and_evidence_instructions() -> None:
    prompt = build_reasoner_prompt(_sample_record())
    combined_prompt = f"{prompt.system_prompt}\n{prompt.user_prompt}"

    for field in OUTPUT_FIELDS:
        assert field in combined_prompt
    for evidence_type in EVIDENCE_TYPES:
        assert evidence_type in combined_prompt
    assert PARSE_MARKER in combined_prompt
    assert "strict JSON" in combined_prompt
    assert "label" in combined_prompt
    assert "0" in combined_prompt
    assert "1" in combined_prompt
    assert "2" in combined_prompt


def test_default_prompt_contains_bias_guard_instructions() -> None:
    prompt = build_reasoner_prompt(_sample_record())
    combined_prompt = f"{prompt.system_prompt}\n{prompt.user_prompt}".lower()

    expected_terms = [
        "protected attribute",
        "appearance",
        "expression",
        "posture",
        "clothing",
        "social background",
    ]
    for term in expected_terms:
        assert term in combined_prompt


def test_default_prompt_clarifies_decisive_evidence_and_uncertainty_boundary() -> None:
    prompt = build_reasoner_prompt(_sample_record())
    combined_prompt = f"{prompt.system_prompt}\n{prompt.user_prompt}".lower()

    expected_terms = [
        "otherwise choose the supported answer",
        "objective visible evidence",
        "valid elimination",
        "only when objective support is insufficient",
        "ordinary clothing",
        "objective visible evidence",
    ]
    for term in expected_terms:
        assert term in combined_prompt


@pytest.mark.parametrize("uncertainty_index", [0, 1, 2])
def test_default_prompt_maps_uncertainty_by_choice_position_not_fixed_label(
    uncertainty_index: int,
) -> None:
    answers = ["Person A", "Person B"]
    answers.insert(uncertainty_index, "Cannot be determined")
    sample = SampleRecord(
        sample_id="uncertainty_first",
        image_path=Path("image.jpg"),
        context="No relevant evidence is available.",
        question="Who is responsible?",
        answers=tuple(answers),  # type: ignore[arg-type]
        row_number=2,
    )

    prompt = build_reasoner_prompt(sample)
    combined_prompt = f"{prompt.system_prompt}\n{prompt.user_prompt}"

    assert f"{uncertainty_index}. Cannot be determined" in combined_prompt
    assert "No numeric label has an inherent person or uncertainty meaning" in combined_prompt
    assert "uncertainty_option_index" in combined_prompt
    assert 'schema_version must be exactly "reasoner_output_v3"' in combined_prompt
    assert "label 2, the uncertainty" not in combined_prompt.lower()


def test_legacy_reasoner_v1_remains_available_for_ab_reproduction() -> None:
    template = load_reasoner_prompt_template(LEGACY_REASONER_PROMPT_PATH)

    assert template.version == "reasoner_v1"


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"unknown": "value"}, "unknown keys"),
        ({"version": ""}, "version"),
        ({"version": "reasoner_v33"}, "version"),
        ({"output_contract": {"fields": ["label"]}}, "output fields"),
        (
            {"output_contract": {"fields": list(OUTPUT_FIELDS), "parse_marker": "BAD_MARKER"}},
            "parse marker",
        ),
        ({"evidence_types": ["bad_evidence"]}, "evidence types"),
        ({"forbidden_sole_support_cues": []}, "forbidden"),
        ({"user_template": "{sample_id} {missing_placeholder}"}, "placeholder"),
        ({"user_template": "{sample_id!r}\n{context}\n{question}\n{answers}"}, "format specs"),
        ({"user_template": "{sample_id:.3}\n{context}\n{question}\n{answers}"}, "format specs"),
        ({"user_template": "{sample_id}"}, "context"),
        (
            {
                "output_contract": {
                    1: "one",
                    "fields": list(OUTPUT_FIELDS),
                    "parse_marker": PARSE_MARKER,
                }
            },
            "output_contract keys",
        ),
    ],
)
def test_load_reasoner_prompt_template_rejects_invalid_templates(
    tmp_path: Path,
    overrides: dict[str, object],
    match: str,
) -> None:
    template_path = _write_template(tmp_path / "bad.yaml", overrides)

    with pytest.raises(ConfigurationError, match=match):
        load_reasoner_prompt_template(template_path)


def test_load_reasoner_prompt_template_rejects_missing_required_key(tmp_path: Path) -> None:
    template_path = tmp_path / "missing-key.yaml"
    content: dict[str, object] = {
        "version": "reasoner_v1",
        "user_template": "{sample_id}\n{context}\n{question}\n{answers}",
        "output_contract": {"fields": list(OUTPUT_FIELDS), "parse_marker": PARSE_MARKER},
        "evidence_types": list(EVIDENCE_TYPES),
        "forbidden_sole_support_cues": list(FORBIDDEN_SOLE_SUPPORT_CUES),
    }
    template_path.write_text(yaml.safe_dump(content, sort_keys=True), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="missing required keys"):
        load_reasoner_prompt_template(template_path)


def test_load_reasoner_prompt_template_rejects_invalid_path() -> None:
    with pytest.raises(ConfigurationError, match="path is invalid"):
        load_reasoner_prompt_template("bad\0path.yaml")


def test_load_reasoner_prompt_template_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    template_path = tmp_path / "duplicate.yaml"
    template_path.write_text(
        """
version: reasoner_v1
version: other
system: Use objective evidence.
user_template: "{sample_id} {context} {question} {answers}"
output_contract:
  parse_marker: FINAL_ANSWER_JSON
  fields:
    - label
    - evidence
    - evidence_type
    - uncertainty_signal
    - protected_attribute_risk
evidence_types:
  - stated_text_fact
  - objective_visible_evidence
  - elimination
  - insufficient_evidence
forbidden_sole_support_cues:
  - protected_attributes
  - appearance
  - expression
  - posture
  - clothing
  - attractiveness
  - social_background
  - perceived_gender
  - perceived_race_or_ethnicity
  - perceived_age
  - body_type
  - stereotype_consistent_assumption
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="duplicate key"):
        load_reasoner_prompt_template(template_path)


def test_load_reasoner_prompt_template_rejects_missing_and_non_mapping(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_reasoner_prompt_template(tmp_path / "missing.yaml")

    list_template_path = tmp_path / "list.yaml"
    list_template_path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="mapping"):
        load_reasoner_prompt_template(list_template_path)


def test_build_reasoner_prompt_rejects_wrong_answer_count() -> None:
    sample = SampleRecord(
        sample_id="bad_answers",
        image_path=Path("image.jpg"),
        context="Context",
        question="Question?",
        answers=("A", "B"),  # type: ignore[arg-type]
        row_number=2,
    )

    with pytest.raises(ConfigurationError, match="exactly 3"):
        build_reasoner_prompt(sample)


def test_default_template_has_no_examples_or_unsupported_keys() -> None:
    raw_template = yaml.safe_load(DEFAULT_REASONER_PROMPT_PATH.read_text(encoding="utf-8"))

    assert set(raw_template) == PROMPT_TEMPLATE_KEYS
    assert not {
        "examples",
        "few_shot_examples",
        "test_examples",
        "evaluation_examples",
        "answer_mappings",
    } & set(raw_template)


def test_default_verifier_prompt_template_loads() -> None:
    template = load_verifier_prompt_template()

    assert template == VerifierPromptTemplate(
        version="verifier_v1",
        system_prompt=template.system_prompt,
        user_template=template.user_template,
        output_contract=template.output_contract,
        evidence_types=EVIDENCE_TYPES,
        forbidden_sole_support_cues=FORBIDDEN_SOLE_SUPPORT_CUES,
    )
    assert template.output_contract.labels == ("0", "1", "2")
    assert template.output_contract.parse_marker == VERIFIER_PARSE_MARKER
    assert template.output_contract.fields == VERIFIER_OUTPUT_FIELDS


def test_build_verifier_prompt_includes_independent_review_context() -> None:
    prompt = build_verifier_prompt(
        _sample_record(),
        _parsed_reasoner_record(),
        ("ambiguous_visual_grounding",),
    )

    assert isinstance(prompt, VerifierPrompt)
    assert prompt.sample_id == "test_0001"
    assert prompt.prompt_version == "verifier_v1"
    assert "test_0001" in prompt.user_prompt
    assert "Who is the medical worker?" in prompt.user_prompt
    assert "ambiguous_visual_grounding" in prompt.user_prompt
    assert "objective_visible_evidence" in prompt.user_prompt
    assert "The first person is holding a stethoscope." in prompt.user_prompt
    combined = f"{prompt.system_prompt}\n{prompt.user_prompt}".lower()
    assert "independent" in combined
    assert "concrete defect" in combined
    assert "protected attribute" in combined
    assert VERIFIER_PARSE_MARKER.lower() in combined
    for field in VERIFIER_OUTPUT_FIELDS:
        assert field in combined


def test_build_verifier_prompt_supports_invalid_reasoner_rows() -> None:
    invalid = ParsedReasonerRecord(
        run_id="run_001",
        sample_id="test_0001",
        parsed_label=None,
        evidence_summary=None,
        evidence_type=None,
        uncertainty_signal=None,
        risk_flags=("invalid_parse",),
        parse_status="invalid_json",
        parse_error="bad JSON",
    )

    prompt = build_verifier_prompt(_sample_record(), invalid, ("invalid_parse",))

    assert "invalid_parse" in prompt.user_prompt
    assert "invalid_json" in prompt.user_prompt
    assert "bad JSON" in prompt.user_prompt
    assert "null" in prompt.user_prompt


def test_default_verifier_template_has_exact_keys_and_no_examples() -> None:
    raw_template = yaml.safe_load(DEFAULT_VERIFIER_PROMPT_PATH.read_text(encoding="utf-8"))

    assert set(raw_template) == VERIFIER_PROMPT_TEMPLATE_KEYS
    assert not {
        "examples",
        "few_shot_examples",
        "test_examples",
        "evaluation_examples",
        "answer_mappings",
    } & set(raw_template)


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        (
            {
                "output_contract": {
                    "fields": list(VERIFIER_OUTPUT_FIELDS),
                    "parse_marker": "BAD_MARKER",
                }
            },
            "parse marker",
        ),
        ({"user_template": "{sample_id}"}, "context"),
        ({"unknown": "value"}, "unknown keys"),
    ],
)
def test_load_verifier_prompt_template_rejects_invalid_templates(
    tmp_path: Path,
    overrides: dict[str, object],
    match: str,
) -> None:
    path = _write_verifier_template(tmp_path / "bad-verifier.yaml", overrides)

    with pytest.raises(ConfigurationError, match=match):
        load_verifier_prompt_template(path)


def test_load_verifier_prompt_template_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate-verifier.yaml"
    path.write_text(
        DEFAULT_VERIFIER_PROMPT_PATH.read_text(encoding="utf-8").replace(
            "version: verifier_v1",
            "version: verifier_v1\nversion: duplicate",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="duplicate key"):
        load_verifier_prompt_template(path)
