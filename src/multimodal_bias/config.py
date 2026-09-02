"""Configuration boundary for runtime settings."""

from pathlib import Path
from typing import Any

import yaml

from multimodal_bias.exceptions import ConfigurationError
from multimodal_bias.run_names import normalize_run_name
from multimodal_bias.schemas import CompetitionConfig

DEFAULT_CONFIG_PATH = Path("configs/base.yaml")
CONFIG_KEYS = frozenset({"data_root", "runs_root", "run_name"})


def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> CompetitionConfig:
    """Load and validate the local runtime configuration file."""

    path = _coerce_config_path(config_path)

    try:
        raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"config file could not be parsed: {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigurationError(f"config file is not readable as UTF-8: {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigurationError(f"config file could not be read: {path}: {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigurationError(f"config file must contain a YAML mapping: {path}")

    non_string_keys = [key for key in raw_config if not isinstance(key, str)]
    if non_string_keys:
        formatted_keys = ", ".join(repr(key) for key in non_string_keys)
        raise ConfigurationError(f"config file keys must be strings: {path}: {formatted_keys}")

    unknown_keys = sorted(set(raw_config) - CONFIG_KEYS)
    if unknown_keys:
        raise ConfigurationError(f"config file has unknown keys: {', '.join(unknown_keys)}")

    return CompetitionConfig(
        data_root=_resolve_path_value(raw_config, "data_root", path),
        runs_root=_resolve_path_value(raw_config, "runs_root", path),
        run_name=normalize_run_name(
            raw_config.get("run_name"),
            source=f"config key run_name in {path}",
        ),
    )


def _coerce_config_path(config_path: Path | str) -> Path:
    try:
        path = Path(config_path).expanduser()
    except (RuntimeError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"config path is invalid: {config_path}: {exc}") from exc
    if "\0" in str(path):
        raise ConfigurationError(f"config path is invalid: {config_path}: embedded NUL")

    try:
        if not path.is_file():
            raise ConfigurationError(f"config file does not exist: {path}")
    except (OSError, ValueError) as exc:
        raise ConfigurationError(f"config path is invalid: {path}: {exc}") from exc

    return path


def _resolve_path_value(raw_config: dict[str, Any], key: str, config_path: Path) -> Path:
    value = raw_config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"config key {key} must be a non-empty path string: {config_path}")
    if "\0" in value:
        raise ConfigurationError(f"config key {key} has invalid path: {config_path}: embedded NUL")
    try:
        return Path(value).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ConfigurationError(
            f"config key {key} has invalid path: {config_path}: {exc}"
        ) from exc
