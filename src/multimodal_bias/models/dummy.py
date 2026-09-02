"""Dummy local model boundary for CPU-safe adapter tests."""

import json
from time import perf_counter

from multimodal_bias.exceptions import InferenceError
from multimodal_bias.models.adapter import validate_generation_max_new_tokens
from multimodal_bias.schemas import (
    ModelConfig,
    ModelGenerationMetadata,
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelLoadMetadata,
)


class DummyVisionLanguageModelAdapter:
    """CPU-safe adapter that returns deterministic raw text for tests."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config
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
            message="dummy adapter not loaded",
        )

    @property
    def load_metadata(self) -> ModelLoadMetadata:
        """Return latest dummy load metadata."""

        return self._load_metadata

    def load(self) -> ModelLoadMetadata:
        """Mark the dummy adapter as locally loaded."""

        self._load_metadata = ModelLoadMetadata(
            model_name=self.config.model_name,
            adapter=self.config.adapter,
            snapshot_path=self.config.snapshot_path,
            revision=self.config.revision,
            snapshot_hash=self.config.snapshot_hash,
            local_files_only=self.config.local_files_only,
            trust_remote_code=self.config.trust_remote_code,
            load_status="loaded",
            device="cpu",
            torch_dtype=self.config.torch_dtype,
            message="dummy adapter loaded without model weights",
        )
        return self._load_metadata

    def generate(self, request: ModelGenerationRequest) -> ModelGenerationResult:
        """Return deterministic raw output without parsing labels."""

        if self._load_metadata.load_status != "loaded":
            raise InferenceError("dummy model adapter is not loaded")
        if not isinstance(request.prompt_text, str) or not request.prompt_text.strip():
            raise InferenceError("dummy model generation requires non-empty prompt text")

        started_at = perf_counter()
        max_new_tokens = validate_generation_max_new_tokens(
            request.max_new_tokens,
            self.config.max_new_tokens,
        )
        diagnostic_text = (
            f"DUMMY_MODEL_OUTPUT model={self.config.model_name} "
            f"prompt={request.prompt_text.strip()}"
        )
        if "FINAL_VERIFICATION_JSON" in request.prompt_text:
            final_marker = "FINAL_VERIFICATION_JSON"
            final_payload = {
                "label": "2",
                "reason": "The dummy adapter cannot verify objective image evidence.",
                "evidence_type": "insufficient_evidence",
                "reasoner_defect_found": True,
                "objective_support": False,
            }
        else:
            final_marker = "FINAL_ANSWER_JSON"
            final_payload = {
                "label": "2",
                "uncertainty_option_index": 2,
                "evidence": "The dummy adapter cannot evaluate objective image evidence.",
                "evidence_type": "insufficient_evidence",
                "uncertainty_signal": True,
                "protected_attribute_risk": False,
                "schema_version": "reasoner_output_v3",
            }
        raw_text = f"{diagnostic_text}\n{final_marker}: " + json.dumps(
            final_payload, ensure_ascii=False, separators=(",", ":")
        )
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
                device="cpu",
                torch_dtype=self.config.torch_dtype,
            ),
        )
