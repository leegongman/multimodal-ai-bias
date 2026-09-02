"""Hugging Face local VLM implementation boundary."""

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


class HuggingFaceLocalVLMAdapter:
    """Local Hugging Face VLM adapter with lazy optional imports."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self._processor: Any | None = None
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
            message="hf_local adapter not loaded",
        )

    @property
    def load_metadata(self) -> ModelLoadMetadata:
        """Return latest Hugging Face load metadata."""

        return self._load_metadata

    def load(self) -> ModelLoadMetadata:
        """Load processor and model from a local snapshot only."""

        try:
            transformers = importlib.import_module("transformers")
        except ImportError as exc:
            self._mark_failed(f"transformers dependency is not installed: {exc}")
            raise ModelLoadError(
                "transformers dependency is required for hf_local adapter; "
                f"{self._load_context()} "
                "action=install transformers-compatible local VLM dependencies"
            ) from exc

        try:
            processor_class = transformers.AutoProcessor
            model_class = getattr(transformers, self.config.model_class)
        except AttributeError as exc:
            self._mark_failed(f"transformers class is unavailable: {exc}")
            raise ModelLoadError(
                f"transformers class unavailable for hf_local adapter: {exc}; "
                f"model_class={self.config.model_class} {self._load_context()} "
                "action=check model_class in model config"
            ) from exc

        processor_kwargs = self._processor_from_pretrained_kwargs()
        model_kwargs = self._model_from_pretrained_kwargs()

        try:
            self._processor = processor_class.from_pretrained(
                self.config.snapshot_path,
                **processor_kwargs,
            )
            self._model = model_class.from_pretrained(
                self.config.snapshot_path,
                **model_kwargs,
            )
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            self._mark_failed(str(exc))
            raise ModelLoadError(
                "local Hugging Face model could not be loaded: "
                f"{self._load_context()}: {exc} "
                "action=verify local snapshot files and optional dependencies"
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
            message="hf_local adapter loaded from local snapshot",
        )
        return self._load_metadata

    def generate(self, request: ModelGenerationRequest) -> ModelGenerationResult:
        """Generate raw text from a loaded local Hugging Face VLM."""

        if self._processor is None or self._model is None:
            raise InferenceError("hf_local model adapter is not loaded")
        if not isinstance(request.prompt_text, str) or not request.prompt_text.strip():
            raise InferenceError("hf_local generation requires non-empty prompt text")

        started_at = perf_counter()
        max_new_tokens = validate_generation_max_new_tokens(
            request.max_new_tokens,
            self.config.max_new_tokens,
        )

        try:
            inputs = self._prepare_inputs(request)
            input_token_count = self._input_token_count(inputs)
            torch = importlib.import_module("torch")
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=self.config.do_sample,
                )
            raw_text, output_token_count = self._decode_generated_text(
                generated_ids,
                input_token_count,
            )
        except Exception as exc:
            raise InferenceError(
                "hf_local generation failed: "
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
                input_token_count=input_token_count,
                output_token_count=output_token_count,
                device=self._model_device(),
                torch_dtype=self.config.torch_dtype,
            ),
        )

    def _processor_from_pretrained_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "local_files_only": True,
            "trust_remote_code": self.config.trust_remote_code,
        }
        if self.config.revision:
            kwargs["revision"] = self.config.revision
        return kwargs

    def _model_from_pretrained_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "local_files_only": True,
            "trust_remote_code": self.config.trust_remote_code,
        }
        if self.config.revision:
            kwargs["revision"] = self.config.revision
        if self.config.device_map:
            kwargs["device_map"] = self.config.device_map
        if self.config.torch_dtype:
            kwargs["torch_dtype"] = self.config.torch_dtype
        return kwargs

    def _prepare_inputs(self, request: ModelGenerationRequest) -> Any:
        image = self._load_optional_image(request)
        messages = [
            {
                "role": "user",
                "content": [
                    *([{"type": "image", "image": image}] if image is not None else []),
                    {"type": "text", "text": request.prompt_text.strip()},
                ],
            }
        ]

        if hasattr(self._processor, "apply_chat_template"):
            inputs = self._processor.apply_chat_template(
                messages,
                **self._chat_template_kwargs(),
            )
        else:
            inputs = self._processor(
                text=request.prompt_text.strip(),
                images=[image] if image is not None else None,
                return_tensors="pt",
            )

        input_device = self._input_device()
        if hasattr(inputs, "to") and input_device is not None:
            return inputs.to(input_device)
        if isinstance(inputs, dict) and input_device is not None:
            return {
                key: value.to(input_device) if hasattr(value, "to") else value
                for key, value in inputs.items()
            }
        return inputs

    def _chat_template_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "add_generation_prompt": True,
            "tokenize": True,
            "return_dict": True,
            "return_tensors": "pt",
        }
        if self.config.model_name == "Qwen/Qwen3.5-9B":
            kwargs["enable_thinking"] = False
        return kwargs

    def _load_optional_image(self, request: ModelGenerationRequest) -> object | None:
        if request.image_path is not None and request.image_bytes is not None:
            raise InferenceError("hf_local generation received both image_path and image_bytes")

        if request.image_path is not None:
            image_path = Path(request.image_path).expanduser()
            if not image_path.is_file():
                raise InferenceError(
                    f"hf_local image_path does not exist or is not a file: {image_path}"
                )
            return str(image_path)
        if request.image_bytes is None:
            return None

        try:
            image_module = importlib.import_module("PIL.Image")
            return image_module.open(BytesIO(request.image_bytes))
        except ImportError as exc:
            raise InferenceError("Pillow is required to load image bytes for hf_local") from exc

    def _decode_generated_text(
        self,
        generated_ids: Any,
        input_token_count: int | None,
    ) -> tuple[str, int | None]:
        candidate_ids = []
        if input_token_count is not None and self._model_returns_prompt_plus_completion():
            try:
                candidate_ids.append(generated_ids[:, input_token_count:])
            except (IndexError, TypeError):
                pass
        candidate_ids.append(generated_ids)

        for output_ids in candidate_ids:
            decoded = self._processor.batch_decode(output_ids, skip_special_tokens=True)
            raw_text = decoded[0].strip() if decoded else ""
            if raw_text:
                return raw_text, self._output_token_count(output_ids)

        raise InferenceError("hf_local generated empty text")

    @staticmethod
    def _input_token_count(inputs: Any) -> int | None:
        input_ids = getattr(inputs, "input_ids", None)
        if input_ids is None and isinstance(inputs, dict):
            input_ids = inputs.get("input_ids")
        try:
            return len(input_ids[0])
        except (IndexError, TypeError):
            return None

    def _model_device(self) -> str | None:
        device = getattr(self._model, "device", None)
        return str(device) if device is not None else None

    def _input_device(self) -> str | None:
        device_map = getattr(self._model, "hf_device_map", None)
        if isinstance(device_map, dict):
            for device in device_map.values():
                if device is not None and str(device) != "disk":
                    return str(device)
        return self._model_device()

    def _model_returns_prompt_plus_completion(self) -> bool:
        model_config = getattr(self._model, "config", None)
        is_encoder_decoder = getattr(model_config, "is_encoder_decoder", None)
        if is_encoder_decoder is True:
            return False
        return True

    @staticmethod
    def _output_token_count(output_ids: Any) -> int | None:
        try:
            return len(output_ids[0])
        except (IndexError, TypeError):
            return None

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
