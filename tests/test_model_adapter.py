import importlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from multimodal_bias.exceptions import ConfigurationError, InferenceError, ModelLoadError
from multimodal_bias.models.adapter import create_model_adapter, load_model_config
from multimodal_bias.models.dummy import DummyVisionLanguageModelAdapter
from multimodal_bias.schemas import (
    ModelConfig,
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelLoadMetadata,
)


def _write_model_config(path: Path, overrides: dict[str, object] | None = None) -> Path:
    snapshot_path = path.parent / "snapshot"
    snapshot_path.mkdir()
    content: dict[str, object] = {
        "adapter": "dummy",
        "model_name": "dummy-vlm",
        "snapshot_path": str(snapshot_path),
        "revision": "",
        "snapshot_hash": "dummy-snapshot",
        "local_files_only": True,
        "trust_remote_code": False,
        "device_map": "cpu",
        "torch_dtype": "auto",
        "max_new_tokens": 16,
        "do_sample": False,
    }
    if overrides:
        content.update(overrides)
    path.write_text(yaml.safe_dump(content, sort_keys=True), encoding="utf-8")
    return path


def test_load_model_config_returns_typed_config(tmp_path: Path) -> None:
    config_path = _write_model_config(tmp_path / "dummy.yaml")

    config = load_model_config(config_path)

    assert config == ModelConfig(
        config_path=config_path.resolve(),
        adapter="dummy",
        model_name="dummy-vlm",
        snapshot_path=(tmp_path / "snapshot").resolve(),
        revision="",
        snapshot_hash="dummy-snapshot",
        local_files_only=True,
        trust_remote_code=False,
        device_map="cpu",
        torch_dtype="auto",
        max_new_tokens=16,
        do_sample=False,
        model_class="AutoModelForImageTextToText",
    )


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"unknown": "value"}, "unknown keys"),
        ({"adapter": "remote_api"}, "adapter"),
        ({"model_name": ""}, "model_name"),
        ({"snapshot_path": "bad\0path"}, "snapshot_path"),
        ({"local_files_only": False}, "local_files_only"),
        ({"trust_remote_code": "false"}, "trust_remote_code"),
        ({"max_new_tokens": 0}, "max_new_tokens"),
        ({"do_sample": "no"}, "do_sample"),
        ({"adapter": "hf_local", "revision": "", "snapshot_hash": ""}, "revision"),
    ],
)
def test_load_model_config_rejects_invalid_contents(
    tmp_path: Path,
    overrides: dict[str, object],
    match: str,
) -> None:
    config_path = _write_model_config(tmp_path / "bad.yaml", overrides)

    with pytest.raises(ConfigurationError, match=match):
        load_model_config(config_path)


def test_load_model_config_rejects_missing_and_non_mapping(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_model_config(tmp_path / "missing.yaml")

    list_config_path = tmp_path / "list.yaml"
    list_config_path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="mapping"):
        load_model_config(list_config_path)


def test_load_model_config_rejects_non_string_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "bad-key.yaml"
    config_path.write_text(
        """
1: one
adapter: dummy
model_name: dummy-vlm
snapshot_path: snapshot
revision: ""
snapshot_hash: dummy-snapshot
local_files_only: true
trust_remote_code: false
device_map: cpu
torch_dtype: auto
max_new_tokens: 16
do_sample: false
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="keys must be strings"):
        load_model_config(config_path)


def test_hf_local_config_requires_existing_snapshot_path(tmp_path: Path) -> None:
    config_path = _write_model_config(
        tmp_path / "hf.yaml",
        {
            "adapter": "hf_local",
            "model_name": "hf-vlm",
            "snapshot_path": str(tmp_path / "missing-snapshot"),
            "revision": "abc123",
            "snapshot_hash": "",
        },
    )

    with pytest.raises(ConfigurationError, match="snapshot_path"):
        load_model_config(config_path)


def test_create_model_adapter_returns_dummy_contract(tmp_path: Path) -> None:
    config = load_model_config(_write_model_config(tmp_path / "dummy.yaml"))

    adapter = create_model_adapter(config)

    assert isinstance(adapter, DummyVisionLanguageModelAdapter)


def test_dummy_adapter_load_and_generate_preserve_raw_text(tmp_path: Path) -> None:
    config = load_model_config(_write_model_config(tmp_path / "dummy.yaml"))
    adapter = DummyVisionLanguageModelAdapter(config)

    load_metadata = adapter.load()
    result = adapter.generate(ModelGenerationRequest(prompt_text="Describe objective evidence."))

    assert isinstance(load_metadata, ModelLoadMetadata)
    assert load_metadata.load_status == "loaded"
    assert load_metadata.local_files_only is True
    assert isinstance(result, ModelGenerationResult)
    assert "Describe objective evidence." in result.raw_text
    final_line = result.raw_text.splitlines()[-1]
    assert final_line.startswith("FINAL_ANSWER_JSON: ")
    payload = json.loads(final_line.removeprefix("FINAL_ANSWER_JSON: "))
    assert payload == {
        "label": "2",
        "uncertainty_option_index": 2,
        "evidence": "The dummy adapter cannot evaluate objective image evidence.",
        "evidence_type": "insufficient_evidence",
        "uncertainty_signal": True,
        "protected_attribute_risk": False,
        "schema_version": "reasoner_output_v3",
    }
    assert result.metadata.max_new_tokens == 16
    assert result.metadata.do_sample is False


def test_dummy_adapter_emits_verifier_contract_for_verifier_prompt(tmp_path: Path) -> None:
    config = load_model_config(_write_model_config(tmp_path / "dummy.yaml"))
    adapter = DummyVisionLanguageModelAdapter(config)
    adapter.load()

    result = adapter.generate(
        ModelGenerationRequest(
            prompt_text="Return a final line beginning with FINAL_VERIFICATION_JSON:"
        )
    )

    final_line = result.raw_text.splitlines()[-1]
    assert final_line.startswith("FINAL_VERIFICATION_JSON: ")
    payload = json.loads(final_line.removeprefix("FINAL_VERIFICATION_JSON: "))
    assert payload == {
        "label": "2",
        "reason": "The dummy adapter cannot verify objective image evidence.",
        "evidence_type": "insufficient_evidence",
        "reasoner_defect_found": True,
        "objective_support": False,
    }


@pytest.mark.parametrize(
    "module_name",
    [
        "multimodal_bias.models.adapter",
        "multimodal_bias.models.dummy",
        "multimodal_bias.models.hf_vlm",
        "multimodal_bias.models.minicpm_v",
    ],
)
def test_model_module_imports_are_optional_dependency_lazy(module_name: str) -> None:
    for loaded_name in [
        "multimodal_bias.models.adapter",
        "multimodal_bias.models.dummy",
        "multimodal_bias.models.hf_vlm",
        "multimodal_bias.models.minicpm_v",
        "torch",
        "transformers",
        "accelerate",
        "PIL",
        "PIL.Image",
    ]:
        sys.modules.pop(loaded_name, None)
    before = set(sys.modules)

    importlib.import_module(module_name)

    imported_during_test = set(sys.modules) - before
    assert "torch" not in imported_during_test
    assert "transformers" not in imported_during_test
    assert "accelerate" not in imported_during_test
    assert "PIL" not in imported_during_test


def test_hf_adapter_missing_transformers_raises_model_load_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_model_config(
        _write_model_config(
            tmp_path / "hf.yaml",
            {"adapter": "hf_local", "model_name": "hf-vlm", "revision": "abc123"},
        )
    )
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> object:
        if name == "transformers":
            raise ImportError("missing transformers")
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    from multimodal_bias.models.hf_vlm import HuggingFaceLocalVLMAdapter

    adapter = HuggingFaceLocalVLMAdapter(config)
    with pytest.raises(ModelLoadError, match="transformers"):
        adapter.load()


def test_qwen35_hf_adapter_disables_thinking_only_for_exact_model(tmp_path: Path) -> None:
    from multimodal_bias.models.hf_vlm import HuggingFaceLocalVLMAdapter

    qwen_config = load_model_config(
        _write_model_config(
            tmp_path / "qwen.yaml",
            {
                "adapter": "hf_local",
                "model_name": "Qwen/Qwen3.5-9B",
                "revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
                "model_class": "AutoModelForMultimodalLM",
            },
        )
    )
    other_config = ModelConfig(
        **{
            **qwen_config.__dict__,
            "model_name": "hf-vlm",
        }
    )

    qwen_kwargs = HuggingFaceLocalVLMAdapter(qwen_config)._chat_template_kwargs()
    other_kwargs = HuggingFaceLocalVLMAdapter(other_config)._chat_template_kwargs()

    assert qwen_kwargs["enable_thinking"] is False
    assert "enable_thinking" not in other_kwargs


def test_hf_adapter_wraps_from_pretrained_import_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_model_config(
        _write_model_config(
            tmp_path / "hf.yaml",
            {"adapter": "hf_local", "model_name": "hf-vlm", "revision": "abc123"},
        )
    )

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, *_args: object, **_kwargs: object) -> object:
            raise ImportError("missing image backend")

    class FakeModel:
        @classmethod
        def from_pretrained(cls, *_args: object, **_kwargs: object) -> object:
            return cls()

    fake_transformers = type(
        "FakeTransformers",
        (),
        {"AutoProcessor": FakeProcessor, "AutoModelForImageTextToText": FakeModel},
    )
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> object:
        if name == "transformers":
            return fake_transformers
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    from multimodal_bias.models.hf_vlm import HuggingFaceLocalVLMAdapter

    adapter = HuggingFaceLocalVLMAdapter(config)
    with pytest.raises(ModelLoadError, match="config_path=.*adapter=hf_local"):
        adapter.load()


def test_dummy_adapter_rejects_invalid_request_max_new_tokens(tmp_path: Path) -> None:
    config = load_model_config(_write_model_config(tmp_path / "dummy.yaml"))
    adapter = DummyVisionLanguageModelAdapter(config)
    adapter.load()

    with pytest.raises(InferenceError, match="max_new_tokens"):
        adapter.generate(ModelGenerationRequest(prompt_text="Prompt", max_new_tokens=0))


def test_hf_adapter_fake_success_uses_local_kwargs_and_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_model_config(
        _write_model_config(
            tmp_path / "hf.yaml",
            {
                "adapter": "hf_local",
                "model_name": "hf-vlm",
                "revision": "abc123",
                "device_map": "auto",
                "torch_dtype": "auto",
                "max_new_tokens": 7,
            },
        )
    )
    records: dict[str, object] = {}

    class FakeIds:
        def __init__(self, rows: list[list[int]]) -> None:
            self.rows = rows

        def __getitem__(self, key: object) -> object:
            if isinstance(key, tuple):
                row_key, column_key = key
                if isinstance(row_key, slice):
                    selected_rows = self.rows[row_key]
                else:
                    selected_rows = [self.rows[row_key]]
                return FakeIds([row[column_key] for row in selected_rows])
            return self.rows[key]

    class FakeTensor:
        def __init__(self) -> None:
            self.moved_to: str | None = None

        def __len__(self) -> int:
            return 1

        def __getitem__(self, _key: object) -> list[int]:
            return [1, 2]

        def to(self, device: str) -> "FakeTensor":
            self.moved_to = device
            records["input_device"] = device
            return self

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, path: Path, **kwargs: object) -> "FakeProcessor":
            records["processor_path"] = path
            records["processor_kwargs"] = kwargs
            return cls()

        def apply_chat_template(self, *_args: object, **_kwargs: object) -> dict[str, object]:
            return {"input_ids": FakeTensor()}

        def batch_decode(self, ids: FakeIds, **_kwargs: object) -> list[str]:
            records["decoded_ids"] = ids.rows
            return ["decoded completion"]

    class FakeModelConfig:
        is_encoder_decoder = False

    class FakeModel:
        config = FakeModelConfig()
        hf_device_map = {"": "cpu"}

        @classmethod
        def from_pretrained(cls, path: Path, **kwargs: object) -> "FakeModel":
            records["model_path"] = path
            records["model_kwargs"] = kwargs
            return cls()

        def generate(self, **kwargs: object) -> FakeIds:
            records["generate_kwargs"] = kwargs
            return FakeIds([[1, 2, 9, 10]])

    class FakeNoGrad:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *_args: object) -> None:
            return None

    fake_transformers = type(
        "FakeTransformers",
        (),
        {"AutoProcessor": FakeProcessor, "AutoModelForImageTextToText": FakeModel},
    )
    fake_torch = type("FakeTorch", (), {"no_grad": staticmethod(lambda: FakeNoGrad())})
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> object:
        if name == "transformers":
            return fake_transformers
        if name == "torch":
            return fake_torch
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    from multimodal_bias.models.hf_vlm import HuggingFaceLocalVLMAdapter

    adapter = HuggingFaceLocalVLMAdapter(config)
    load_metadata = adapter.load()
    result = adapter.generate(ModelGenerationRequest(prompt_text="Prompt", max_new_tokens=5))

    assert load_metadata.load_status == "loaded"
    assert records["processor_kwargs"] == {
        "local_files_only": True,
        "trust_remote_code": False,
        "revision": "abc123",
    }
    assert records["model_kwargs"] == {
        "local_files_only": True,
        "trust_remote_code": False,
        "revision": "abc123",
        "device_map": "auto",
        "torch_dtype": "auto",
    }
    assert records["input_device"] == "cpu"
    assert records["decoded_ids"] == [[9, 10]]
    assert result.raw_text == "decoded completion"
    assert result.metadata.max_new_tokens == 5
    assert result.metadata.model_name == "hf-vlm"


def test_hf_adapter_rejects_ambiguous_or_missing_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_model_config(
        _write_model_config(
            tmp_path / "hf.yaml",
            {"adapter": "hf_local", "model_name": "hf-vlm", "revision": "abc123"},
        )
    )

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, *_args: object, **_kwargs: object) -> "FakeProcessor":
            return cls()

        def __call__(self, **_kwargs: object) -> dict[str, object]:
            return {"input_ids": [1, 2]}

    class FakeModel:
        @classmethod
        def from_pretrained(cls, *_args: object, **_kwargs: object) -> "FakeModel":
            return cls()

    fake_transformers = type(
        "FakeTransformers",
        (),
        {"AutoProcessor": FakeProcessor, "AutoModelForImageTextToText": FakeModel},
    )
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> object:
        if name == "transformers":
            return fake_transformers
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    from multimodal_bias.models.hf_vlm import HuggingFaceLocalVLMAdapter

    adapter = HuggingFaceLocalVLMAdapter(config)
    adapter.load()

    with pytest.raises(InferenceError, match="both image_path and image_bytes"):
        adapter.generate(
            ModelGenerationRequest(
                prompt_text="Prompt",
                image_path=tmp_path / "missing.jpg",
                image_bytes=b"image",
            )
        )

    with pytest.raises(InferenceError, match="image_path"):
        adapter.generate(
            ModelGenerationRequest(prompt_text="Prompt", image_path=tmp_path / "missing.jpg")
        )


def test_create_model_adapter_returns_minicpm_contract(tmp_path: Path) -> None:
    config = load_model_config(
        _write_model_config(
            tmp_path / "minicpm.yaml",
            {
                "adapter": "minicpm_v",
                "model_name": "MiniCPM-V-4_5",
                "revision": "abc123",
                "trust_remote_code": True,
                "model_class": "AutoModel",
            },
        )
    )

    adapter = create_model_adapter(config)

    from multimodal_bias.models.minicpm_v import MiniCPMVLocalAdapter

    assert isinstance(adapter, MiniCPMVLocalAdapter)


def test_minicpm_adapter_fake_success_uses_local_snapshot_and_chat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_model_config(
        _write_model_config(
            tmp_path / "minicpm.yaml",
            {
                "adapter": "minicpm_v",
                "model_name": "MiniCPM-V-4_5",
                "revision": "abc123",
                "trust_remote_code": True,
                "device_map": "auto",
                "torch_dtype": "bfloat16",
                "max_new_tokens": 17,
                "model_class": "AutoModel",
            },
        )
    )
    records: dict[str, object] = {}

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, path: Path, **kwargs: object) -> "FakeTokenizer":
            records["tokenizer_path"] = path
            records["tokenizer_kwargs"] = kwargs
            return cls()

    class FakeModel:
        device = "cuda:0"

        @classmethod
        def from_pretrained(cls, path: Path, **kwargs: object) -> "FakeModel":
            records["model_path"] = path
            records["model_kwargs"] = kwargs
            return cls()

        def eval(self) -> "FakeModel":
            records["eval_called"] = True
            return self

        def chat(self, **kwargs: object) -> str:
            records["chat_kwargs"] = kwargs
            return (
                "FINAL_ANSWER_JSON: "
                '{"label":"2","evidence":"x","evidence_type":"insufficient_evidence",'
                '"uncertainty_signal":true,"protected_attribute_risk":false}'
            )

    class FakeImage:
        def convert(self, mode: str) -> "FakeImage":
            records["image_convert_mode"] = mode
            return self

    class FakeImageModule:
        @staticmethod
        def open(source: object) -> FakeImage:
            records["image_source_type"] = type(source).__name__
            return FakeImage()

    fake_transformers = type(
        "FakeTransformers",
        (),
        {"AutoTokenizer": FakeTokenizer, "AutoModel": FakeModel},
    )
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> object:
        if name == "transformers":
            return fake_transformers
        if name == "PIL.Image":
            return FakeImageModule
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    from multimodal_bias.models.minicpm_v import MiniCPMVLocalAdapter

    adapter = MiniCPMVLocalAdapter(config)
    load_metadata = adapter.load()
    result = adapter.generate(
        ModelGenerationRequest(prompt_text="Prompt", image_bytes=b"image", max_new_tokens=11)
    )

    assert load_metadata.load_status == "loaded"
    assert records["tokenizer_kwargs"] == {
        "local_files_only": True,
        "trust_remote_code": True,
        "revision": "abc123",
    }
    assert records["model_kwargs"] == {
        "local_files_only": True,
        "trust_remote_code": True,
        "revision": "abc123",
        "device_map": "auto",
        "torch_dtype": "bfloat16",
    }
    assert records["eval_called"] is True
    assert records["image_convert_mode"] == "RGB"
    assert records["image_source_type"] == "BytesIO"
    assert records["chat_kwargs"]["enable_thinking"] is False
    assert records["chat_kwargs"]["stream"] is False
    assert records["chat_kwargs"]["sampling"] is False
    assert records["chat_kwargs"]["max_new_tokens"] == 11
    assert result.raw_text.startswith("FINAL_ANSWER_JSON:")
    assert result.metadata.adapter == "minicpm_v"
    assert result.metadata.model_name == "MiniCPM-V-4_5"


def test_minicpm_adapter_retries_chat_without_max_new_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_model_config(
        _write_model_config(
            tmp_path / "minicpm.yaml",
            {
                "adapter": "minicpm_v",
                "model_name": "MiniCPM-V-4_5",
                "revision": "abc123",
                "trust_remote_code": True,
            },
        )
    )
    attempts: list[dict[str, object]] = []

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, *_args: object, **_kwargs: object) -> "FakeTokenizer":
            return cls()

    class FakeModel:
        @classmethod
        def from_pretrained(cls, *_args: object, **_kwargs: object) -> "FakeModel":
            return cls()

        def eval(self) -> "FakeModel":
            return self

        def chat(self, **kwargs: object) -> str:
            attempts.append(kwargs)
            if "max_new_tokens" in kwargs:
                raise TypeError("unexpected keyword argument 'max_new_tokens'")
            return "fallback text"

    class FakeImage:
        def convert(self, _mode: str) -> "FakeImage":
            return self

    class FakeImageModule:
        @staticmethod
        def open(_source: object) -> FakeImage:
            return FakeImage()

    fake_transformers = type(
        "FakeTransformers",
        (),
        {"AutoTokenizer": FakeTokenizer, "AutoModel": FakeModel},
    )
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> object:
        if name == "transformers":
            return fake_transformers
        if name == "PIL.Image":
            return FakeImageModule
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    from multimodal_bias.models.minicpm_v import MiniCPMVLocalAdapter

    adapter = MiniCPMVLocalAdapter(config)
    adapter.load()
    result = adapter.generate(ModelGenerationRequest(prompt_text="Prompt", image_bytes=b"image"))

    assert "max_new_tokens" in attempts[0]
    assert "max_new_tokens" not in attempts[1]
    assert result.raw_text == "fallback text"
