"""Prompt safety guard constants."""

from types import MappingProxyType

from multimodal_bias.schemas import EvidenceType

REASONER_OUTPUT_SCHEMA_VERSION = "reasoner_output_v3"
REASONER_PROMPT_SCHEMA_MODES = MappingProxyType(
    {"reasoner_v1": "v2", "reasoner_v2": "v2", "reasoner_v3": "v3"}
)
LEGACY_OUTPUT_FIELDS = (
    "label",
    "evidence",
    "evidence_type",
    "uncertainty_signal",
    "protected_attribute_risk",
)
OUTPUT_FIELDS = (
    "label",
    "uncertainty_option_index",
    "evidence",
    "evidence_type",
    "uncertainty_signal",
    "protected_attribute_risk",
    "schema_version",
)
PARSE_MARKER = "FINAL_ANSWER_JSON"

EVIDENCE_TYPES: tuple[EvidenceType, ...] = (
    "stated_text_fact",
    "objective_visible_evidence",
    "elimination",
    "insufficient_evidence",
)

FORBIDDEN_SOLE_SUPPORT_CUES = (
    "protected_attributes",
    "appearance",
    "expression",
    "posture",
    "clothing",
    "attractiveness",
    "social_background",
    "perceived_gender",
    "perceived_race_or_ethnicity",
    "perceived_age",
    "body_type",
    "stereotype_consistent_assumption",
)

PROMPT_TEMPLATE_KEYS = frozenset(
    {
        "version",
        "system",
        "user_template",
        "output_contract",
        "evidence_types",
        "forbidden_sole_support_cues",
    }
)

USER_TEMPLATE_PLACEHOLDERS = frozenset({"sample_id", "context", "question", "answers"})

VERIFIER_OUTPUT_FIELDS = (
    "label",
    "reason",
    "evidence_type",
    "reasoner_defect_found",
    "objective_support",
)
VERIFIER_PARSE_MARKER = "FINAL_VERIFICATION_JSON"
VERIFIER_PROMPT_TEMPLATE_KEYS = PROMPT_TEMPLATE_KEYS
VERIFIER_USER_TEMPLATE_PLACEHOLDERS = frozenset(
    {
        "sample_id",
        "context",
        "question",
        "answers",
        "reasoner_label",
        "reasoner_evidence",
        "reasoner_evidence_type",
        "reasoner_uncertainty_signal",
        "reasoner_parse_status",
        "reasoner_parse_error",
        "triggers",
    }
)
