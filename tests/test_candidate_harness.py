import hashlib
import json
import struct
import zlib
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

import multimodal_bias.candidate_harness as candidate_harness_module
from multimodal_bias.candidate_harness import (
    load_candidate_manifest,
    run_candidate_smoke,
    write_candidate_report,
)
from multimodal_bias.exceptions import CandidateEligibilityError
from multimodal_bias.schemas import (
    CandidateHardwareTelemetry,
    ModelConfig,
    ModelGenerationMetadata,
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelLoadMetadata,
)


class FakeAdapter:
    def __init__(self, config: ModelConfig, raw_text: str) -> None:
        self.config = config
        self.raw_text = raw_text
        self._metadata = ModelLoadMetadata(
            config.model_name,
            config.adapter,
            config.snapshot_path,
            config.revision,
            config.snapshot_hash,
            True,
            False,
            "not_loaded",
            None,
            "auto",
        )

    @property
    def load_metadata(self) -> ModelLoadMetadata:
        return self._metadata

    def load(self) -> ModelLoadMetadata:
        self._metadata = ModelLoadMetadata(
            self.config.model_name,
            self.config.adapter,
            self.config.snapshot_path,
            self.config.revision,
            self.config.snapshot_hash,
            True,
            False,
            "loaded",
            "cuda:0",
            "bfloat16",
        )
        return self._metadata

    def generate(self, request: ModelGenerationRequest) -> ModelGenerationResult:
        assert request.image_bytes
        assert request.image_path is not None and request.image_path.is_file()
        assert request.image_format == "png"
        assert "FINAL_ANSWER_JSON" in request.prompt_text
        return ModelGenerationResult(
            self.raw_text,
            ModelGenerationMetadata(
                self.config.adapter,
                self.config.model_name,
                64,
                False,
                0.2,
                device="cuda:0",
                torch_dtype="bfloat16",
            ),
        )


class FailingLoadAdapter(FakeAdapter):
    def load(self) -> ModelLoadMetadata:
        raise RuntimeError("offline snapshot cannot load")


class FailingGenerationAdapter(FakeAdapter):
    def generate(self, request: ModelGenerationRequest) -> ModelGenerationResult:
        raise RuntimeError("generation crashed")


class MissingLoadMetadataAdapter(FakeAdapter):
    def load(self):
        return None


class MismatchedIdentityAdapter(FakeAdapter):
    def load(self) -> ModelLoadMetadata:
        metadata = super().load()
        self._metadata = replace(metadata, snapshot_hash="c" * 64)
        return self._metadata


def _write_valid_image(path: Path) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00\x0c\x22\x38")
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")
    )


def _manifest_file(tmp_path: Path, **overrides: object) -> Path:
    lock = tmp_path / "uv.lock"
    lock.write_text("locked", encoding="utf-8")
    data: dict[str, object] = {
        "candidate_id": "qwen-control",
        "official_repo": "https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct",
        "commit": "a" * 40,
        "release_date": "2025-01-01",
        "cutoff_evidence": "official release page",
        "license_id": "apache-2.0",
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
        "snapshot_sha256": "b" * 64,
        "custom_code_hashes": {},
        "dependency_lock_path": str(lock),
        "processor_evidence": "AutoProcessor official path",
        "chat_template_evidence": "apply_chat_template official path",
        "image_serialization_evidence": "processor images argument",
        "preprocessing_metadata": {"min_pixels": "200704", "max_pixels": "602112"},
        "remote_api_usage": "none",
    }
    data.update(overrides)
    path = tmp_path / "candidate.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _model_config(tmp_path: Path) -> ModelConfig:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    return ModelConfig(
        tmp_path / "model.yaml",
        "dummy",
        "candidate",
        snapshot,
        "a" * 40,
        "b" * 64,
        True,
        False,
        "cuda:0",
        "bfloat16",
        64,
        False,
    )


def _valid_raw() -> str:
    payload = {
        "label": "2",
        "uncertainty_option_index": 2,
        "evidence": "The smoke input does not identify either person.",
        "evidence_type": "insufficient_evidence",
        "uncertainty_signal": True,
        "protected_attribute_risk": False,
        "schema_version": "reasoner_output_v3",
    }
    return "FINAL_ANSWER_JSON:" + json.dumps(payload, separators=(",", ":"))


def test_candidate_smoke_passes_all_gates_with_injected_a6000(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    image = tmp_path / "real.png"
    _write_valid_image(image)
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=FakeAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 17000),
    )
    assert report.diagnostic_48_allowed is True
    assert report.rejections == ()
    assert report.rendered_input is not None
    assert report.rendered_input.image_sha256 == hashlib.sha256(image.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "overrides,code",
    [
        ({"remote_api_usage": "openai"}, "remote_api_forbidden"),
        ({"release_date": "2026-06-01"}, "cutoff_ineligible"),
        ({"commit": "main"}, "commit_unpinned"),
    ],
)
def test_candidate_manifest_rejects_ineligible_metadata(
    tmp_path: Path, overrides: dict[str, object], code: str
) -> None:
    with pytest.raises(CandidateEligibilityError) as exc_info:
        load_candidate_manifest(_manifest_file(tmp_path, **overrides))
    assert exc_info.value.code == code


@pytest.mark.parametrize(
    "overrides,code",
    [
        ({"dependency_lock_path": "/missing/uv.lock"}, "dependency_lock_missing"),
        ({"snapshot_sha256": "not-a-hash"}, "snapshot_hash_invalid"),
        ({"processor_evidence": ""}, "serialization_evidence_missing"),
        ({"preprocessing_metadata": {}}, "serialization_evidence_missing"),
    ],
)
def test_candidate_manifest_rejects_missing_or_malformed_local_evidence(
    tmp_path: Path, overrides: dict[str, object], code: str
) -> None:
    with pytest.raises(CandidateEligibilityError) as exc_info:
        load_candidate_manifest(_manifest_file(tmp_path, **overrides))
    assert exc_info.value.code == code


def test_candidate_manifest_rejects_duplicate_and_extra_fields(tmp_path: Path) -> None:
    duplicate = _manifest_file(tmp_path)
    duplicate.write_text(
        duplicate.read_text(encoding="utf-8") + "candidate_id: duplicate\n",
        encoding="utf-8",
    )
    with pytest.raises(CandidateEligibilityError) as duplicate_error:
        load_candidate_manifest(duplicate)
    assert duplicate_error.value.code == "manifest_invalid"

    extra = _manifest_file(tmp_path, unexpected="field")
    with pytest.raises(CandidateEligibilityError) as extra_error:
        load_candidate_manifest(extra)
    assert extra_error.value.code == "manifest_invalid"


def test_candidate_manifest_rejects_invalid_types_and_custom_hashes(tmp_path: Path) -> None:
    invalid_type = _manifest_file(tmp_path, official_repo=123)
    with pytest.raises(CandidateEligibilityError) as type_error:
        load_candidate_manifest(invalid_type)
    assert type_error.value.code == "manifest_invalid"

    invalid_hash = _manifest_file(tmp_path, custom_code_hashes={"model.py": "bad"})
    with pytest.raises(CandidateEligibilityError) as hash_error:
        load_candidate_manifest(invalid_hash)
    assert hash_error.value.code == "custom_code_hash_invalid"


def test_candidate_manifest_rejects_non_utf8_file(tmp_path: Path) -> None:
    path = tmp_path / "candidate.yaml"
    path.write_bytes(b"candidate_id: \xff")
    with pytest.raises(CandidateEligibilityError) as exc_info:
        load_candidate_manifest(path)
    assert exc_info.value.code == "manifest_invalid"


def test_candidate_manifest_resolves_relative_evidence_and_verifies_custom_code(
    tmp_path: Path,
) -> None:
    custom = tmp_path / "custom.py"
    custom.write_text("VALUE = 1\n", encoding="utf-8")
    custom_hash = hashlib.sha256(custom.read_bytes()).hexdigest()
    manifest = load_candidate_manifest(
        _manifest_file(
            tmp_path,
            dependency_lock_path="uv.lock",
            custom_code_hashes={"custom.py": custom_hash},
        )
    )
    assert manifest.dependency_lock_path == (tmp_path / "uv.lock").resolve()

    custom.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(CandidateEligibilityError) as exc_info:
        load_candidate_manifest(
            _manifest_file(
                tmp_path,
                dependency_lock_path="uv.lock",
                custom_code_hashes={"custom.py": custom_hash},
            )
        )
    assert exc_info.value.code == "custom_code_hash_mismatch"


@pytest.mark.parametrize(
    "overrides",
    [
        {"release_date": "2025-W01-1"},
        {"preprocessing_metadata": {"key": "\ud800"}},
        {"preprocessing_metadata": {"key": "one", " key ": "two"}},
    ],
)
def test_candidate_manifest_rejects_noncanonical_or_unsafe_text(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    with pytest.raises(CandidateEligibilityError) as exc_info:
        load_candidate_manifest(_manifest_file(tmp_path, **overrides))
    assert exc_info.value.code == "manifest_invalid"


def test_candidate_manifest_maps_unhashable_yaml_key_to_stable_error(tmp_path: Path) -> None:
    path = tmp_path / "candidate.yaml"
    path.write_text("? [a, b]\n: value\n", encoding="utf-8")
    with pytest.raises(CandidateEligibilityError) as exc_info:
        load_candidate_manifest(path)
    assert exc_info.value.code == "manifest_invalid"


def test_candidate_smoke_blocks_non_a6000_and_invalid_output(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    image = tmp_path / "real.png"
    _write_valid_image(image)
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=FakeAdapter(config, "not structured"),
        hardware=CandidateHardwareTelemetry("NVIDIA L4", 23034, 1000),
    )
    assert report.diagnostic_48_allowed is False
    assert {item.code for item in report.rejections} == {
        "structured_output_invalid",
        "gpu_not_a6000",
        "vram_insufficient",
    }


def test_candidate_smoke_reports_offline_load_failure_without_generation(
    tmp_path: Path,
) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    image = tmp_path / "real.png"
    _write_valid_image(image)
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=FailingLoadAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert report.diagnostic_48_allowed is False
    assert [item.code for item in report.rejections] == ["offline_load_failed"]
    assert report.raw_output is None


def test_candidate_smoke_reports_invalid_image_without_loading_adapter(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    report = run_candidate_smoke(
        manifest,
        config,
        tmp_path / "missing.png",
        adapter=FakeAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert report.diagnostic_48_allowed is False
    assert [item.code for item in report.rejections] == ["image_invalid"]
    assert report.load_metadata is None


def test_candidate_smoke_rejects_signature_only_image_without_loading_adapter(
    tmp_path: Path,
) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    image = tmp_path / "truncated.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nnot-an-image")
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=FakeAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert [item.code for item in report.rejections] == ["image_invalid"]
    assert report.load_metadata is None


def test_candidate_smoke_fails_closed_on_config_and_load_identity(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)

    dummy_report = run_candidate_smoke(
        manifest,
        config,
        tmp_path / "unused.png",
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert [item.code for item in dummy_report.rejections] == ["adapter_ineligible"]

    network_report = run_candidate_smoke(
        manifest,
        replace(config, local_files_only=False),
        tmp_path / "unused.png",
        adapter=FakeAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert [item.code for item in network_report.rejections] == ["remote_api_forbidden"]

    image = tmp_path / "real.png"
    _write_valid_image(image)
    missing_metadata = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=MissingLoadMetadataAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert [item.code for item in missing_metadata.rejections] == ["offline_load_failed"]

    mismatched_identity = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=MismatchedIdentityAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert [item.code for item in mismatched_identity.rejections] == ["load_identity_mismatch"]


def test_candidate_smoke_requires_custom_code_evidence_when_enabled(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = replace(_model_config(tmp_path), trust_remote_code=True)
    report = run_candidate_smoke(
        manifest,
        config,
        tmp_path / "unused.png",
        adapter=FakeAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert [item.code for item in report.rejections] == ["custom_code_evidence_missing"]


def test_candidate_smoke_maps_adapter_creation_failure_to_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = replace(_model_config(tmp_path), adapter="hf_local")
    image = tmp_path / "real.png"
    _write_valid_image(image)

    def fail_adapter(_config: ModelConfig):
        raise RuntimeError("adapter construction failed")

    monkeypatch.setattr(candidate_harness_module, "create_model_adapter", fail_adapter)
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert [item.code for item in report.rejections] == ["offline_load_failed"]


def test_candidate_smoke_requires_exact_gpu_and_peak_memory(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    image = tmp_path / "real.png"
    _write_valid_image(image)
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=FakeAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NOT RTX A6000", 49140, None),
    )
    assert {item.code for item in report.rejections} == {
        "gpu_not_a6000",
        "peak_vram_missing",
    }


def test_candidate_smoke_stops_before_generation_on_snapshot_mismatch(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    config = ModelConfig(
        config.config_path,
        config.adapter,
        config.model_name,
        config.snapshot_path,
        config.revision,
        "c" * 64,
        config.local_files_only,
        config.trust_remote_code,
        config.device_map,
        config.torch_dtype,
        config.max_new_tokens,
        config.do_sample,
    )
    image = tmp_path / "real.png"
    _write_valid_image(image)
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=FailingGenerationAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert report.diagnostic_48_allowed is False
    assert [item.code for item in report.rejections] == ["snapshot_hash_mismatch"]
    assert report.raw_output is None


def test_candidate_smoke_reports_generation_failure(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    image = tmp_path / "real.png"
    _write_valid_image(image)
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=FailingGenerationAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 0),
    )
    assert [item.code for item in report.rejections] == ["generation_failed"]
    assert report.raw_output is None


def test_candidate_report_is_no_clobber_json(tmp_path: Path) -> None:
    manifest = load_candidate_manifest(_manifest_file(tmp_path))
    config = _model_config(tmp_path)
    image = tmp_path / "real.png"
    _write_valid_image(image)
    report = run_candidate_smoke(
        manifest,
        config,
        image,
        adapter=FakeAdapter(config, _valid_raw()),
        hardware=CandidateHardwareTelemetry("NVIDIA RTX A6000", 49140, 17000),
    )
    output = tmp_path / "candidate_smoke.json"
    write_candidate_report(report, output)
    first = output.read_bytes()
    assert json.loads(first)["diagnostic_48_allowed"] is True
    with pytest.raises(CandidateEligibilityError, match="already exists"):
        write_candidate_report(report, output)
    assert output.read_bytes() == first

    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("file", encoding="utf-8")
    with pytest.raises(CandidateEligibilityError) as exc_info:
        write_candidate_report(report, blocked_parent / "report.json")
    assert exc_info.value.code == "report_write_failed"
