"""Run name normalization shared across config and run logging."""

import re

from multimodal_bias.exceptions import ConfigurationError

_SAFE_RUN_NAME = re.compile(r"^[a-z0-9_]+$")


def normalize_run_name(value: object, *, source: str) -> str:
    """Normalize and validate a filesystem-safe run name."""

    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{source} must be a non-empty string")

    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")

    if not normalized or not _SAFE_RUN_NAME.fullmatch(normalized):
        raise ConfigurationError(
            f"{source} must normalize to lowercase ASCII letters, digits, and underscores"
        )

    return normalized
