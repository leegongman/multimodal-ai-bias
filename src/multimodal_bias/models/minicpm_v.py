"""MiniCPM-V local Hugging Face adapter."""

from __future__ import annotations

import importlib
from io import BytesIO
from pathlib import Path
from time import perf_counter
from typing import Any

from multimodal_bias.exceptions import InferenceError, ModelLoadError
from multimodal_bias.models.adapter import validate_generation_max_new_tokens
from multimodal_bias.schemas import (
    ModelConfig,
    ModelGenerationMetadata,
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelLoadMetadata,
)


class MiniCPMVLocalAdapter:
    """Local MiniCPM-V adapter using its `model.chat` interface."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._load_metadata = ModelLoadMetadata(
            model_name=config.model_name,
            adapter=config.adapter,
            snapshot_path=config.snapshot_path,
            revision=config.revision,
            snapshot_hash=config.snapshot_hash,
            local_files_only=config.local_files_only,
            trust_remote_code=config.trust_remote_code,
            load_status="not_loaded",
            device=None,
            torch_dtype=config.torch_dtype,
            message="minicpm_v adapter not loaded",
        )

    @property
    def load_metadata(self) -> ModelLoadMetadata:
        """Return latest MiniCPM-V load metadata."""

        return self._load_metadata

    def load(self) -> ModelLoadMetadata:
        """Load MiniCPM-V model and tokenizer from a local snapshot."""

        try:
            transformers = importlib.import_module("transformers")
        except ImportError as exc:
            self._mark_failed(f"transformers dependency is not installed: {exc}")
            raise ModelLoadError(
                "transformers dependency is required for minicpm_v adapter; "
                f"{self._load_context()} "
                "action=install MiniCPM-V-compatible local dependencies"
            ) from exc

        try:
            tokenizer_class = transformers.AutoTokenizer
            model_class = transformers.AutoModel
        except AttributeError as exc:
            self._mark_failed(f"transformers class is unavailable: {exc}")
            raise ModelLoadError(
                f"transformers class unavailable for minicpm_v adapter: {exc}; "
                f"{self._load_context()} action=check transformers installation"
            ) from exc

        tokenizer_kwargs = self._from_pretrained_kwargs(include_device=False)
        model_kwargs = self._from_pretrained_kwargs(include_device=True)

        try:
            self._tokenizer = tokenizer_class.from_pretrained(
                self.config.snapshot_path,
                **tokenizer_kwargs,
            )
            self._model = model_class.from_pretrained(
                self.config.snapshot_path,
                **model_kwargs,
            )
            if hasattr(self._model, "eval"):
                self._model = self._model.eval()
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            self._mark_failed(str(exc))
            raise ModelLoadError(
                "local MiniCPM-V model could not be loaded: "
                f"{self._load_context()}: {exc} "
                "action=verify local snapshot files, trust_remote_code, and optional dependencies"
            ) from exc

        self._load_metadata = ModelLoadMetadata(
            model_name=self.config.model_name,
            adapter=self.config.adapter,
            snapshot_path=self.config.snapshot_path,
            revision=self.config.revision,
            snapshot_hash=self.config.snapshot_hash,
            local_files_only=self.config.local_files_only,
            trust_remote_code=self.config.trust_remote_code,
            load_status="loaded",
            device=self._model_device(),
            torch_dtype=self.config.torch_dtype,
            message="minicpm_v adapter loaded from local snapshot",
        )
        return self._load_metadata

    def generate(self, request: ModelGenerationRequest) -> ModelGenerationResult:
        """Generate raw text through MiniCPM-V `chat`."""

        if self._tokenizer is None or self._model is None:
            raise InferenceError("minicpm_v model adapter is not loaded")
        if not isinstance(request.prompt_text, str) or not request.prompt_text.strip():
            raise InferenceError("minicpm_v generation requires non-empty prompt text")
        if not hasattr(self._model, "chat"):
            raise InferenceError("minicpm_v loaded model does not expose chat()")

        started_at = perf_counter()
        max_new_tokens = validate_generation_max_new_tokens(
            request.max_new_tokens,
            self.config.max_new_tokens,
        )

        try:
            image = self._load_optional_image(request)
            msgs = [{"role": "user", "content": [image, request.prompt_text.strip()]}]
            raw_response = self._chat(msgs, max_new_tokens)
            raw_text = self._coerce_raw_text(raw_response)
        except Exception as exc:
            raise InferenceError(
                "minicpm_v generation failed: "
                f"model_name={self.config.model_name} "
                f"snapshot_path={self.config.snapshot_path}: {exc}"
            ) from exc

        elapsed_seconds = perf_counter() - started_at
        return ModelGenerationResult(
            raw_text=raw_text,
            metadata=ModelGenerationMetadata(
                adapter=self.config.adapter,
                model_name=self.config.model_name,
                max_new_tokens=max_new_tokens,
                do_sample=self.config.do_sample,
                elapsed_seconds=elapsed_seconds,
                input_token_count=None,
                output_token_count=None,
                device=self._model_device(),
                torch_dtype=self.config.torch_dtype,
            ),
        )

    def _from_pretrained_kwargs(self, *, include_device: bool) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "local_files_only": True,
            "trust_remote_code": self.config.trust_remote_code,
        }
        if self.config.revision:
            kwargs["revision"] = self.config.revision
        if include_device:
            if self.config.device_map:
                kwargs["device_map"] = self.config.device_map
            if self.config.torch_dtype:
                kwargs["torch_dtype"] = self.config.torch_dtype
        return kwargs

    def _chat(self, msgs: list[dict[str, object]], max_new_tokens: int) -> object:
        chat_kwargs: dict[str, object] = {
            "msgs": msgs,
            "tokenizer": self._tokenizer,
            "enable_thinking": False,
            "stream": False,
            "sampling": self.config.do_sample,
            "max_new_tokens": max_new_tokens,
        }
        try:
            return self._model.chat(**chat_kwargs)
        except TypeError as exc:
            if "max_new_tokens" not in str(exc):
                raise
            chat_kwargs.pop("max_new_tokens")
            return self._model.chat(**chat_kwargs)

    def _load_optional_image(self, request: ModelGenerationRequest) -> object:
        if request.image_path is not None and request.image_bytes is not None:
            raise InferenceError("minicpm_v generation received both image_path and image_bytes")

        try:
            image_module = importlib.import_module("PIL.Image")
        except ImportError as exc:
            raise InferenceError("Pillow is required to load images for minicpm_v") from exc

        try:
            if request.image_path is not None:
                image_path = Path(request.image_path).expanduser()
                if not image_path.is_file():
                    raise InferenceError(
                        f"minicpm_v image_path does not exist or is not a file: {image_path}"
                    )
                return image_module.open(image_path).convert("RGB")
            if request.image_bytes is not None:
                return image_module.open(BytesIO(request.image_bytes)).convert("RGB")
        except InferenceError:
            raise
        except Exception as exc:
            raise InferenceError(f"minicpm_v image could not be loaded: {exc}") from exc

        raise InferenceError("minicpm_v generation requires an image")

    @staticmethod
    def _coerce_raw_text(raw_response: object) -> str:
        if isinstance(raw_response, str):
            raw_text = raw_response.strip()
        elif isinstance(raw_response, list | tuple):
            raw_text = "".join(str(part) for part in raw_response).strip()
        else:
            raw_text = str(raw_response).strip()

        if not raw_text:
            raise InferenceError("minicpm_v generated empty text")
        return raw_text

    def _model_device(self) -> str | None:
        device = getattr(self._model, "device", None)
        return str(device) if device is not None else None

    def _load_context(self) -> str:
        return (
            f"config_path={self.config.config_path} "
            f"model_name={self.config.model_name} "
            f"snapshot_path={self.config.snapshot_path} "
            f"adapter={self.config.adapter}"
        )

    def _mark_failed(self, message: str) -> None:
        self._load_metadata = ModelLoadMetadata(
            model_name=self.config.model_name,
            adapter=self.config.adapter,
            snapshot_path=self.config.snapshot_path,
            revision=self.config.revision,
            snapshot_hash=self.config.snapshot_hash,
            local_files_only=self.config.local_files_only,
            trust_remote_code=self.config.trust_remote_code,
            load_status="failed",
            device=None,
            torch_dtype=self.config.torch_dtype,
            message=message,
        )
