"""Vision-language model adapter boundary."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import yaml

from multimodal_bias.exceptions import ConfigurationError, InferenceError, ModelLoadError
from multimodal_bias.schemas import (
    ModelAdapterType,
    ModelConfig,
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelLoadMetadata,
)

DEFAULT_MODEL_CONFIG_PATH = Path("configs/models/example_vlm.yaml")
MODEL_CONFIG_KEYS = frozenset(
    {
        "adapter",
        "model_name",
        "snapshot_path",
        "revision",
        "snapshot_hash",
        "local_files_only",
        "trust_remote_code",
        "device_map",
        "torch_dtype",
        "max_new_tokens",
        "do_sample",
        "model_class",
    }
)
MODEL_REQUIRED_CONFIG_KEYS = MODEL_CONFIG_KEYS - {"model_class"}
MODEL_ADAPTER_TYPES: tuple[ModelAdapterType, ...] = ("dummy", "hf_local", "minicpm_v")
DEFAULT_MODEL_CLASS = "AutoModelForImageTextToText"
MAX_SMOKE_TOKENS = 4096


class VisionLanguageModelAdapter(Protocol):
    """Model-agnostic local VLM adapter contract."""

    config: ModelConfig

    @property
    def load_metadata(self) -> ModelLoadMetadata:
        """Return the latest load metadata for this adapter."""

    def load(self) -> ModelLoadMetadata:
        """Load local model resources and return audit metadata."""

    def generate(self, request: ModelGenerationRequest) -> ModelGenerationResult:
        """Return raw generated text and generation metadata."""


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


def load_model_config(config_path: Path | str = DEFAULT_MODEL_CONFIG_PATH) -> ModelConfig:
    """Load and validate a local model adapter config file."""

    path = _coerce_model_config_path(config_path)

    try:
        raw_config = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"model config could not be parsed: {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigurationError(f"model config is not readable as UTF-8: {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigurationError(f"model config could not be read: {path}: {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigurationError(f"model config must contain a YAML mapping: {path}")

    non_string_keys = [key for key in raw_config if not isinstance(key, str)]
    if non_string_keys:
        formatted_keys = ", ".join(repr(key) for key in non_string_keys)
        raise ConfigurationError(f"model config keys must be strings: {path}: {formatted_keys}")

    unknown_keys = sorted(set(raw_config) - MODEL_CONFIG_KEYS)
    if unknown_keys:
        raise ConfigurationError(f"model config has unknown keys: {', '.join(unknown_keys)}")

    missing_keys = sorted(MODEL_REQUIRED_CONFIG_KEYS - set(raw_config))
    if missing_keys:
        raise ConfigurationError(f"model config missing required keys: {', '.join(missing_keys)}")

    adapter = _validate_adapter(raw_config, path)
    revision = _required_string(raw_config, "revision", path, allow_empty=True)
    snapshot_hash = _required_string(raw_config, "snapshot_hash", path, allow_empty=True)

    if adapter in {"hf_local", "minicpm_v"} and not revision and not snapshot_hash:
        raise ConfigurationError(
            f"model config requires revision or snapshot_hash for {adapter}: {path}"
        )

    local_files_only = _required_bool(raw_config, "local_files_only", path)
    if not local_files_only:
        raise ConfigurationError(f"model config local_files_only must be true: {path}")

    return ModelConfig(
        config_path=path.resolve(),
        adapter=adapter,
        model_name=_required_string(raw_config, "model_name", path),
        snapshot_path=_resolve_snapshot_path(raw_config, path),
        revision=revision,
        snapshot_hash=snapshot_hash,
        local_files_only=local_files_only,
        trust_remote_code=_required_bool(raw_config, "trust_remote_code", path),
        device_map=_required_string(raw_config, "device_map", path),
        torch_dtype=_required_string(raw_config, "torch_dtype", path),
        max_new_tokens=_validate_max_new_tokens(raw_config, path),
        do_sample=_required_bool(raw_config, "do_sample", path),
        model_class=_required_string(raw_config, "model_class", path)
        if "model_class" in raw_config
        else DEFAULT_MODEL_CLASS,
    )


def create_model_adapter(config: ModelConfig) -> VisionLanguageModelAdapter:
    """Create a local model adapter from validated config."""

    if config.adapter == "dummy":
        from multimodal_bias.models.dummy import DummyVisionLanguageModelAdapter

        return DummyVisionLanguageModelAdapter(config)

    if config.adapter == "hf_local":
        from multimodal_bias.models.hf_vlm import HuggingFaceLocalVLMAdapter

        return HuggingFaceLocalVLMAdapter(config)

    if config.adapter == "minicpm_v":
        from multimodal_bias.models.minicpm_v import MiniCPMVLocalAdapter

        return MiniCPMVLocalAdapter(config)

    raise ModelLoadError(f"unsupported model adapter: {config.adapter}")


def validate_generation_max_new_tokens(value: object, default: int) -> int:
    """Validate a per-request generation token override."""

    if value is None:
        return default

    if not isinstance(value, int) or isinstance(value, bool):
        raise InferenceError("generation max_new_tokens override must be an integer")

    if value < 1 or value > MAX_SMOKE_TOKENS:
        raise InferenceError(
            f"generation max_new_tokens override must be between 1 and {MAX_SMOKE_TOKENS}"
        )

    return value


def _coerce_model_config_path(config_path: Path | str) -> Path:
    try:
        path = Path(config_path).expanduser()
    except (RuntimeError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"model config path is invalid: {config_path}: {exc}") from exc

    if "\0" in str(path):
        raise ConfigurationError(f"model config path is invalid: {config_path}: embedded NUL")

    try:
        if not path.is_file():
            raise ConfigurationError(f"model config file does not exist: {path}")
    except (OSError, ValueError) as exc:
        raise ConfigurationError(f"model config path is invalid: {path}: {exc}") from exc

    return path


def _validate_adapter(raw_config: dict[str, Any], path: Path) -> ModelAdapterType:
    value = raw_config.get("adapter")
    if value not in MODEL_ADAPTER_TYPES:
        expected = ", ".join(MODEL_ADAPTER_TYPES)
        raise ConfigurationError(f"model config adapter must be one of {expected}: {path}")
    return value


def _required_string(
    raw_config: dict[str, Any],
    key: str,
    path: Path,
    *,
    allow_empty: bool = False,
) -> str:
    value = raw_config.get(key)
    if not isinstance(value, str):
        raise ConfigurationError(f"model config key {key} must be a string: {path}")
    cleaned = value.strip()
    if not allow_empty and not cleaned:
        raise ConfigurationError(f"model config key {key} must be a non-empty string: {path}")
    return cleaned


def _required_bool(raw_config: dict[str, Any], key: str, path: Path) -> bool:
    value = raw_config.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"model config key {key} must be a boolean: {path}")
    return value


def _resolve_snapshot_path(raw_config: dict[str, Any], path: Path) -> Path:
    value = _required_string(raw_config, "snapshot_path", path)
    if "\0" in value:
        raise ConfigurationError(f"model config snapshot_path is invalid: {path}: embedded NUL")

    try:
        snapshot_path = Path(value).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ConfigurationError(f"model config snapshot_path is invalid: {path}: {exc}") from exc

    if not snapshot_path.is_dir():
        raise ConfigurationError(
            f"model config snapshot_path must be an existing local directory: {snapshot_path}"
        )

    return snapshot_path


def _validate_max_new_tokens(raw_config: dict[str, Any], path: Path) -> int:
    value = raw_config.get("max_new_tokens")
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigurationError(f"model config max_new_tokens must be an integer: {path}")
    if value < 1 or value > MAX_SMOKE_TOKENS:
        raise ConfigurationError(
            f"model config max_new_tokens must be between 1 and {MAX_SMOKE_TOKENS}: {path}"
        )
    return value
