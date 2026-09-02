"""Prompt template loading and construction."""

from __future__ import annotations

from pathlib import Path
from string import Formatter
from typing import Any

import yaml

from multimodal_bias.exceptions import ConfigurationError
from multimodal_bias.prompting.guards import (
    EVIDENCE_TYPES,
    FORBIDDEN_SOLE_SUPPORT_CUES,
    LEGACY_OUTPUT_FIELDS,
    OUTPUT_FIELDS,
    PARSE_MARKER,
    PROMPT_TEMPLATE_KEYS,
    REASONER_PROMPT_SCHEMA_MODES,
    USER_TEMPLATE_PLACEHOLDERS,
    VERIFIER_OUTPUT_FIELDS,
    VERIFIER_PARSE_MARKER,
    VERIFIER_PROMPT_TEMPLATE_KEYS,
    VERIFIER_USER_TEMPLATE_PLACEHOLDERS,
)
from multimodal_bias.schemas import (
    ParsedReasonerRecord,
    ReasonerOutputContract,
    ReasonerPrompt,
    ReasonerPromptTemplate,
    SampleRecord,
    VerificationTrigger,
    VerifierOutputContract,
    VerifierPrompt,
    VerifierPromptTemplate,
)

DEFAULT_REASONER_PROMPT_PATH = Path("configs/prompts/reasoner_v3.yaml")
DEFAULT_VERIFIER_PROMPT_PATH = Path("configs/prompts/verifier_v1.yaml")
PROMPT_LABELS = ("0", "1", "2")


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    seen_keys: set[object] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            already_seen = key in seen_keys
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found unhashable key {key!r}",
                key_node.start_mark,
            ) from exc
        if already_seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        seen_keys.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_reasoner_prompt_template(
    template_path: Path | str = DEFAULT_REASONER_PROMPT_PATH,
) -> ReasonerPromptTemplate:
    """Load and validate a versioned Reasoner prompt template."""

    path = _coerce_template_path(template_path)

    try:
        raw_template = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=_UniqueKeySafeLoader,
        )
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"prompt template could not be parsed: {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigurationError(
            f"prompt template is not readable as UTF-8: {path}: {exc}"
        ) from exc
    except OSError as exc:
        raise ConfigurationError(f"prompt template could not be read: {path}: {exc}") from exc

    if not isinstance(raw_template, dict):
        raise ConfigurationError(f"prompt template must contain a YAML mapping: {path}")

    non_string_keys = [key for key in raw_template if not isinstance(key, str)]
    if non_string_keys:
        formatted_keys = ", ".join(repr(key) for key in non_string_keys)
        raise ConfigurationError(f"prompt template keys must be strings: {path}: {formatted_keys}")

    unknown_keys = sorted(set(raw_template) - PROMPT_TEMPLATE_KEYS)
    if unknown_keys:
        raise ConfigurationError(f"prompt template has unknown keys: {', '.join(unknown_keys)}")

    missing_keys = sorted(PROMPT_TEMPLATE_KEYS - set(raw_template))
    if missing_keys:
        raise ConfigurationError(
            f"prompt template missing required keys: {', '.join(missing_keys)}"
        )

    version = _required_non_empty_string(raw_template, "version", path)
    if version not in REASONER_PROMPT_SCHEMA_MODES:
        raise ConfigurationError(
            "prompt template version must be exactly one of: "
            + ", ".join(REASONER_PROMPT_SCHEMA_MODES)
        )
    return ReasonerPromptTemplate(
        version=version,
        system_prompt=_required_non_empty_string(raw_template, "system", path),
        user_template=_validate_user_template(
            _required_non_empty_string(raw_template, "user_template", path),
            path,
        ),
        output_contract=_validate_output_contract(raw_template["output_contract"], path, version),
        evidence_types=_validate_evidence_types(raw_template["evidence_types"], path),
        forbidden_sole_support_cues=_validate_forbidden_cues(
            raw_template["forbidden_sole_support_cues"],
            path,
        ),
    )


def _coerce_template_path(template_path: Path | str) -> Path:
    try:
        path = Path(template_path).expanduser()
    except (RuntimeError, TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"prompt template path is invalid: {template_path}: {exc}"
        ) from exc

    if "\0" in str(path):
        raise ConfigurationError(f"prompt template path is invalid: {template_path}: embedded NUL")

    try:
        if not path.is_file():
            raise ConfigurationError(f"prompt template file does not exist: {path}")
    except (OSError, ValueError) as exc:
        raise ConfigurationError(f"prompt template path is invalid: {path}: {exc}") from exc

    return path


def build_reasoner_prompt(
    sample: SampleRecord,
    template_path: Path | str = DEFAULT_REASONER_PROMPT_PATH,
) -> ReasonerPrompt:
    """Build an evidence-grounded Reasoner prompt for one sample."""

    template = load_reasoner_prompt_template(template_path)
    user_prompt = template.user_template.format(
        sample_id=sample.sample_id,
        context=sample.context,
        question=sample.question,
        answers=_format_answers(sample.answers),
    )
    return ReasonerPrompt(
        sample_id=sample.sample_id,
        prompt_version=template.version,
        system_prompt=template.system_prompt,
        user_prompt=user_prompt,
        output_contract=template.output_contract,
    )


def load_verifier_prompt_template(
    template_path: Path | str = DEFAULT_VERIFIER_PROMPT_PATH,
) -> VerifierPromptTemplate:
    """Load and validate a versioned Verifier prompt template."""

    path = _coerce_template_path(template_path)
    try:
        raw_template = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=_UniqueKeySafeLoader,
        )
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"prompt template could not be parsed: {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigurationError(
            f"prompt template is not readable as UTF-8: {path}: {exc}"
        ) from exc
    except OSError as exc:
        raise ConfigurationError(f"prompt template could not be read: {path}: {exc}") from exc

    if not isinstance(raw_template, dict):
        raise ConfigurationError(f"prompt template must contain a YAML mapping: {path}")
    if any(not isinstance(key, str) for key in raw_template):
        raise ConfigurationError(f"prompt template keys must be strings: {path}")

    unknown_keys = sorted(set(raw_template) - VERIFIER_PROMPT_TEMPLATE_KEYS)
    if unknown_keys:
        raise ConfigurationError(f"prompt template has unknown keys: {', '.join(unknown_keys)}")
    missing_keys = sorted(VERIFIER_PROMPT_TEMPLATE_KEYS - set(raw_template))
    if missing_keys:
        raise ConfigurationError(
            f"prompt template missing required keys: {', '.join(missing_keys)}"
        )

    return VerifierPromptTemplate(
        version=_required_non_empty_string(raw_template, "version", path),
        system_prompt=_required_non_empty_string(raw_template, "system", path),
        user_template=_validate_template_placeholders(
            _required_non_empty_string(raw_template, "user_template", path),
            path,
            VERIFIER_USER_TEMPLATE_PLACEHOLDERS,
        ),
        output_contract=_validate_verifier_output_contract(raw_template["output_contract"], path),
        evidence_types=_validate_evidence_types(raw_template["evidence_types"], path),
        forbidden_sole_support_cues=_validate_forbidden_cues(
            raw_template["forbidden_sole_support_cues"], path
        ),
    )


def build_verifier_prompt(
    sample: SampleRecord,
    reasoner_record: ParsedReasonerRecord,
    triggers: tuple[VerificationTrigger, ...],
    template_path: Path | str = DEFAULT_VERIFIER_PROMPT_PATH,
) -> VerifierPrompt:
    """Build an independent Verifier prompt for one triggered sample."""

    if sample.sample_id != reasoner_record.sample_id:
        raise ConfigurationError("Verifier sample and Reasoner record sample_id must match")
    if not isinstance(triggers, tuple) or not triggers:
        raise ConfigurationError("Verifier prompt requires at least one trigger")

    template = load_verifier_prompt_template(template_path)
    user_prompt = template.user_template.format(
        sample_id=sample.sample_id,
        context=sample.context,
        question=sample.question,
        answers=_format_answers(sample.answers),
        reasoner_label=_optional_text(reasoner_record.parsed_label),
        reasoner_evidence=_optional_text(reasoner_record.evidence_summary),
        reasoner_evidence_type=_optional_text(reasoner_record.evidence_type),
        reasoner_uncertainty_signal=_optional_text(reasoner_record.uncertainty_signal),
        reasoner_parse_status=reasoner_record.parse_status,
        reasoner_parse_error=_optional_text(reasoner_record.parse_error),
        triggers=", ".join(triggers),
    )
    return VerifierPrompt(
        sample_id=sample.sample_id,
        prompt_version=template.version,
        system_prompt=template.system_prompt,
        user_prompt=user_prompt,
        output_contract=template.output_contract,
    )


def _required_non_empty_string(raw_template: dict[str, Any], key: str, path: Path) -> str:
    value = raw_template.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"prompt template key {key} must be a non-empty string: {path}")
    return value.strip()


def _validate_user_template(value: str, path: Path) -> str:
    return _validate_template_placeholders(value, path, USER_TEMPLATE_PLACEHOLDERS)


def _validate_template_placeholders(
    value: str,
    path: Path,
    expected_placeholders: frozenset[str],
) -> str:
    try:
        parsed_fields = {
            field_name for _, field_name, _, _ in Formatter().parse(value) if field_name is not None
        }
        invalid_specs = [
            field_name
            for _, field_name, format_spec, conversion in Formatter().parse(value)
            if field_name is not None and (format_spec or conversion)
        ]
    except ValueError as exc:
        raise ConfigurationError(
            f"prompt template has malformed placeholder: {path}: {exc}"
        ) from exc

    if invalid_specs:
        raise ConfigurationError(
            "prompt template placeholders must not use conversion or format specs: "
            + ", ".join(sorted(invalid_specs))
        )

    unknown_fields = sorted(parsed_fields - expected_placeholders)
    if unknown_fields:
        raise ConfigurationError(
            f"prompt template has unknown placeholder names: {', '.join(unknown_fields)}"
        )

    missing_fields = sorted(expected_placeholders - parsed_fields)
    if missing_fields:
        raise ConfigurationError(
            f"prompt template missing required placeholder names: {', '.join(missing_fields)}"
        )

    return value


def _validate_output_contract(
    value: object, path: Path, template_version: str
) -> ReasonerOutputContract:
    if not isinstance(value, dict):
        raise ConfigurationError(f"prompt template output_contract must be a mapping: {path}")

    non_string_keys = [key for key in value if not isinstance(key, str)]
    if non_string_keys:
        formatted_keys = ", ".join(repr(key) for key in non_string_keys)
        raise ConfigurationError(
            f"prompt template output_contract keys must be strings: {path}: {formatted_keys}"
        )

    unknown_contract_keys = sorted(set(value) - {"fields", "parse_marker"})
    if unknown_contract_keys:
        raise ConfigurationError(
            "prompt template output_contract has unknown keys: " + ", ".join(unknown_contract_keys)
        )

    fields = value.get("fields")
    if not isinstance(fields, list) or any(not isinstance(field, str) for field in fields):
        raise ConfigurationError(f"prompt template output fields must be a string list: {path}")

    expected_fields = (
        OUTPUT_FIELDS
        if REASONER_PROMPT_SCHEMA_MODES[template_version] == "v3"
        else LEGACY_OUTPUT_FIELDS
    )
    if tuple(fields) != expected_fields:
        raise ConfigurationError(
            "prompt template output fields must be exactly: " + ", ".join(expected_fields)
        )

    parse_marker = value.get("parse_marker")
    if parse_marker != PARSE_MARKER:
        raise ConfigurationError(
            f"prompt template parse marker must be exactly {PARSE_MARKER}: {path}"
        )

    return ReasonerOutputContract(
        labels=PROMPT_LABELS,
        parse_marker=PARSE_MARKER,
        fields=expected_fields,
        evidence_types=EVIDENCE_TYPES,
    )


def _validate_verifier_output_contract(
    value: object,
    path: Path,
) -> VerifierOutputContract:
    if not isinstance(value, dict):
        raise ConfigurationError(f"prompt template output_contract must be a mapping: {path}")
    if any(not isinstance(key, str) for key in value):
        raise ConfigurationError(f"prompt template output_contract keys must be strings: {path}")
    unknown_keys = sorted(set(value) - {"fields", "parse_marker"})
    if unknown_keys:
        raise ConfigurationError(
            "prompt template output_contract has unknown keys: " + ", ".join(unknown_keys)
        )
    fields = value.get("fields")
    if not isinstance(fields, list) or any(not isinstance(field, str) for field in fields):
        raise ConfigurationError(f"prompt template output fields must be a string list: {path}")
    if tuple(fields) != VERIFIER_OUTPUT_FIELDS:
        raise ConfigurationError(
            "prompt template output fields must be exactly: " + ", ".join(VERIFIER_OUTPUT_FIELDS)
        )
    parse_marker = value.get("parse_marker")
    if parse_marker != VERIFIER_PARSE_MARKER:
        raise ConfigurationError(
            f"prompt template parse marker must be exactly {VERIFIER_PARSE_MARKER}: {path}"
        )
    return VerifierOutputContract(
        labels=PROMPT_LABELS,
        parse_marker=VERIFIER_PARSE_MARKER,
        fields=VERIFIER_OUTPUT_FIELDS,
        evidence_types=EVIDENCE_TYPES,
    )


def _validate_evidence_types(value: object, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConfigurationError(f"prompt template evidence types must be a string list: {path}")

    if tuple(value) != EVIDENCE_TYPES:
        raise ConfigurationError(
            "prompt template evidence types must be exactly: " + ", ".join(EVIDENCE_TYPES)
        )

    return EVIDENCE_TYPES


def _validate_forbidden_cues(value: object, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConfigurationError(f"prompt template forbidden cues must be a string list: {path}")

    if tuple(value) != FORBIDDEN_SOLE_SUPPORT_CUES:
        raise ConfigurationError(
            "prompt template forbidden cues must be exactly: "
            + ", ".join(FORBIDDEN_SOLE_SUPPORT_CUES)
        )

    return FORBIDDEN_SOLE_SUPPORT_CUES


def _format_answers(answers: tuple[str, str, str]) -> str:
    if len(answers) != 3:
        raise ConfigurationError("sample answers must contain exactly 3 choices")
    if any(not isinstance(answer, str) or not answer.strip() for answer in answers):
        raise ConfigurationError("sample answers must contain exactly 3 non-empty strings")
    return "\n".join(f"{index}. {answer}" for index, answer in enumerate(answers))


def _optional_text(value: object | None) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)
