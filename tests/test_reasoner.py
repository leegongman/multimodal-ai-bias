import csv
import json
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from multimodal_bias.config import load_config
from multimodal_bias.exceptions import ConfigurationError, InferenceError
from multimodal_bias.models.adapter import load_model_config
from multimodal_bias.reasoner import (
    RAW_REASONER_FILENAME,
    RAW_REASONER_PARTIAL_FILENAME,
    run_reasoner_inference,
)
from multimodal_bias.run_logging import start_run
from multimodal_bias.schemas import (
    ModelConfig,
    ModelGenerationMetadata,
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelLoadMetadata,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\nminimal-png"
CORRUPT_IMAGE_BYTES = b"not image bytes"
RAW_REASONER_KEYS = {
    "run_id",
    "sample_id",
    "prompt_version",
    "prompt_text",
    "prompt_sha256",
    "image_path",
    "image_status",
    "image_sha256",
    "image_byte_count",
    "image_format",
    "raw_output",
    "generation_metadata",
    "model_load_metadata",
    "elapsed_seconds",
    "status",
    "error_type",
    "error_message",
}
FORBIDDEN_OUTPUT_KEYS = {
    "label",
    "parsed_label",
    "final_label",
    "parse_status",
    "verifier_trigger",
    "arbitration",
}


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_open_layout(tmp_path: Path, image_payloads: list[bytes | None]) -> Path:
    data_root = tmp_path / "open"
    (data_root / "train/images").mkdir(parents=True)
    (data_root / "test/images").mkdir(parents=True)
    (data_root / "train/images/train_img_0000.png").write_bytes(PNG_BYTES)

    answers = json.dumps(["first person", "second person", "uncertain"])
    _write_csv(
        data_root / "train/train.csv",
        ["sample_id", "image_path", "context", "question", "answers", "label"],
        [
            {
                "sample_id": "train_0000",
                "image_path": "train/images/train_img_0000.png",
                "context": "A training context.",
                "question": "Who is described?",
                "answers": answers,
                "label": "0",
            }
        ],
    )

    test_rows = []
    submission_rows = []
    for index, image_payload in enumerate(image_payloads):
        sample_id = f"test_{index:04d}"
        image_name = f"test_img_{index:04d}.png"
        if image_payload is not None:
            (data_root / "test/images" / image_name).write_bytes(image_payload)
        test_rows.append(
            {
                "sample_id": sample_id,
                "image_path": f"test/images/{image_name}",
                "context": f"A test context for {sample_id}.",
                "question": "Who is described?",
                "answers": answers,
            }
        )
        submission_rows.append({"sample_id": sample_id, "label": "0"})

    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        test_rows,
    )
    _write_csv(data_root / "sample_submission.csv", ["sample_id", "label"], submission_rows)
    return data_root


def _write_runtime_config(path: Path, data_root: Path, runs_root: Path) -> Path:
    path.write_text(
        f"""
data_root: {data_root}
runs_root: {runs_root}
run_name: reasoner smoke
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _write_model_config(path: Path) -> Path:
    snapshot_path = path.parent / "snapshot"
    snapshot_path.mkdir()
    content = {
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
    path.write_text(yaml.safe_dump(content, sort_keys=True), encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _prepared_run(
    tmp_path: Path,
    image_payloads: list[bytes | None],
) -> tuple[Path, ModelConfig, object]:
    data_root = _build_open_layout(tmp_path, image_payloads)
    runtime_config_path = _write_runtime_config(
        tmp_path / "config.yaml",
        data_root,
        tmp_path / "runs",
    )
    model_config = load_model_config(_write_model_config(tmp_path / "model.yaml"))
    runtime_config = load_config(runtime_config_path)
    manifest = start_run(runtime_config, config_path=runtime_config_path)
    return runtime_config_path, model_config, manifest


def test_run_reasoner_inference_writes_successful_raw_jsonl_rows(tmp_path: Path) -> None:
    runtime_config_path, model_config, manifest = _prepared_run(tmp_path, [PNG_BYTES, PNG_BYTES])
    runtime_config = load_config(runtime_config_path)

    result = run_reasoner_inference(runtime_config, model_config, manifest)

    assert result.manifest == manifest
    assert result.raw_reasoner_path == manifest.run_dir / RAW_REASONER_FILENAME
    assert result.total_samples == 2
    assert result.generated_count == 2
    assert result.failure_count == 0
    assert result.raw_reasoner_path.is_file()

    rows = _read_jsonl(result.raw_reasoner_path)
    assert [row["sample_id"] for row in rows] == ["test_0000", "test_0001"]
    for row in rows:
        assert set(row) == RAW_REASONER_KEYS
        assert row["run_id"] == manifest.run_id
        assert row["prompt_version"] == "reasoner_v3"
        assert isinstance(row["prompt_text"], str)
        assert row["prompt_sha256"] == sha256(row["prompt_text"].encode("utf-8")).hexdigest()
        assert row["image_status"] == "loaded"
        assert row["image_sha256"] == sha256(PNG_BYTES).hexdigest()
        assert row["image_byte_count"] == len(PNG_BYTES)
        assert row["image_format"] == "png"
        assert row["status"] == "generated"
        assert row["error_type"] is None
        assert row["error_message"] is None
        assert isinstance(row["elapsed_seconds"], float)
        assert row["elapsed_seconds"] >= 0
        assert isinstance(row["raw_output"], str)
        assert "DUMMY_MODEL_OUTPUT" in row["raw_output"]
        assert "Sample ID:" in row["raw_output"]
        assert row["generation_metadata"]["adapter"] == "dummy"
        assert row["generation_metadata"]["model_name"] == "dummy-vlm"
        assert row["model_load_metadata"]["load_status"] == "loaded"
        assert row["model_load_metadata"]["model_name"] == "dummy-vlm"
        assert FORBIDDEN_OUTPUT_KEYS.isdisjoint(row)

    assert not (manifest.run_dir / RAW_REASONER_PARTIAL_FILENAME).exists()

    for downstream_name in (
        "parsed_reasoner.csv",
        "verification.jsonl",
        "final_predictions.csv",
        "submission.csv",
    ):
        assert not (manifest.run_dir / downstream_name).exists()


def test_run_reasoner_inference_logs_image_failures_without_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_config_path, model_config, manifest = _prepared_run(
        tmp_path,
        [PNG_BYTES, None, CORRUPT_IMAGE_BYTES, PNG_BYTES],
    )
    runtime_config = load_config(runtime_config_path)
    adapter = RecordingAdapter(model_config)
    monkeypatch.setattr("multimodal_bias.reasoner.create_model_adapter", lambda _config: adapter)

    result = run_reasoner_inference(runtime_config, model_config, manifest)

    rows = _read_jsonl(result.raw_reasoner_path)
    assert [row["sample_id"] for row in rows] == [
        "test_0000",
        "test_0001",
        "test_0002",
        "test_0003",
    ]
    assert [row["status"] for row in rows] == [
        "generated",
        "image_failed",
        "image_failed",
        "generated",
    ]
    assert [_extract_sample_id(request.prompt_text) for request in adapter.generated_requests] == [
        "test_0000",
        "test_0003",
    ]
    assert adapter.generated_requests[0].image_path is None
    assert adapter.generated_requests[0].image_bytes == PNG_BYTES
    assert adapter.generated_requests[0].image_format == "png"
    assert adapter.load_count == 1
    assert result.generated_count == 2
    assert result.failure_count == 2

    missing_row = rows[1]
    assert missing_row["prompt_version"] == "reasoner_v3"
    assert missing_row["prompt_text"] is None
    assert missing_row["prompt_sha256"] is None
    assert missing_row["image_status"] == "missing"
    assert missing_row["image_sha256"] is None
    assert missing_row["image_byte_count"] is None
    assert missing_row["image_format"] is None
    assert missing_row["raw_output"] is None
    assert missing_row["generation_metadata"] is None
    assert missing_row["model_load_metadata"]["load_status"] == "loaded"
    assert missing_row["status"] == "image_failed"
    assert missing_row["error_type"] == "ImageLoadError"
    assert "does not exist" in missing_row["error_message"]
    assert FORBIDDEN_OUTPUT_KEYS.isdisjoint(missing_row)

    corrupt_row = rows[2]
    assert corrupt_row["prompt_version"] == "reasoner_v3"
    assert corrupt_row["image_status"] == "corrupt"
    assert corrupt_row["raw_output"] is None
    assert corrupt_row["generation_metadata"] is None
    assert corrupt_row["model_load_metadata"]["load_status"] == "loaded"
    assert corrupt_row["status"] == "image_failed"
    assert corrupt_row["error_type"] == "ImageLoadError"
    assert "corrupt" in corrupt_row["error_message"]
    assert FORBIDDEN_OUTPUT_KEYS.isdisjoint(corrupt_row)


def test_run_reasoner_inference_logs_inference_failures_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_config_path, model_config, manifest = _prepared_run(
        tmp_path,
        [PNG_BYTES, PNG_BYTES, PNG_BYTES],
    )
    runtime_config = load_config(runtime_config_path)
    adapter = RecordingAdapter(model_config, fail_sample_id="test_0001")
    monkeypatch.setattr("multimodal_bias.reasoner.create_model_adapter", lambda _config: adapter)

    result = run_reasoner_inference(runtime_config, model_config, manifest)

    rows = _read_jsonl(result.raw_reasoner_path)
    assert [row["sample_id"] for row in rows] == ["test_0000", "test_0001", "test_0002"]
    assert [row["status"] for row in rows] == ["generated", "inference_failed", "generated"]
    assert result.generated_count == 2
    assert result.failure_count == 1

    failed_row = rows[1]
    assert failed_row["image_status"] == "loaded"
    assert failed_row["prompt_text"]
    assert (
        failed_row["prompt_sha256"] == sha256(failed_row["prompt_text"].encode("utf-8")).hexdigest()
    )
    assert failed_row["image_sha256"] == sha256(PNG_BYTES).hexdigest()
    assert failed_row["image_byte_count"] == len(PNG_BYTES)
    assert failed_row["image_format"] == "png"
    assert failed_row["raw_output"] is None
    assert failed_row["generation_metadata"] is None
    assert failed_row["model_load_metadata"]["load_status"] == "loaded"
    assert failed_row["error_type"] == "InferenceError"
    assert "planned failure for test_0001" in failed_row["error_message"]
    assert rows[2]["raw_output"] == "raw output for test_0002"


def test_run_reasoner_inference_logs_prompt_failures_per_sample(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_config_path, model_config, manifest = _prepared_run(tmp_path, [PNG_BYTES, PNG_BYTES])
    runtime_config = load_config(runtime_config_path)
    adapter = RecordingAdapter(model_config)

    def fail_second_prompt(sample: object, template_path: Path | str):
        if sample.sample_id == "test_0001":
            raise ConfigurationError("prompt construction failed for test_0001")
        return original_build_reasoner_prompt(sample, template_path)

    from multimodal_bias.reasoner import build_reasoner_prompt as original_build_reasoner_prompt

    monkeypatch.setattr("multimodal_bias.reasoner.create_model_adapter", lambda _config: adapter)
    monkeypatch.setattr("multimodal_bias.reasoner.build_reasoner_prompt", fail_second_prompt)

    result = run_reasoner_inference(runtime_config, model_config, manifest)

    rows = _read_jsonl(result.raw_reasoner_path)
    assert [row["status"] for row in rows] == ["generated", "prompt_failed"]
    assert [_extract_sample_id(request.prompt_text) for request in adapter.generated_requests] == [
        "test_0000"
    ]
    assert result.generated_count == 1
    assert result.failure_count == 1
    assert rows[1]["prompt_version"] == "reasoner_v3"
    assert rows[1]["prompt_text"] is None
    assert rows[1]["prompt_sha256"] is None
    assert rows[1]["image_sha256"] == sha256(PNG_BYTES).hexdigest()
    assert rows[1]["raw_output"] is None
    assert rows[1]["generation_metadata"] is None
    assert rows[1]["model_load_metadata"]["load_status"] == "loaded"
    assert rows[1]["error_type"] == "ConfigurationError"
    assert "prompt construction failed" in rows[1]["error_message"]


def test_run_reasoner_inference_does_not_leave_final_raw_file_on_unexpected_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_config_path, model_config, manifest = _prepared_run(tmp_path, [PNG_BYTES, PNG_BYTES])
    runtime_config = load_config(runtime_config_path)
    adapter = RecordingAdapter(model_config, unexpected_fail_sample_id="test_0001")
    monkeypatch.setattr("multimodal_bias.reasoner.create_model_adapter", lambda _config: adapter)

    with pytest.raises(RuntimeError, match="unexpected failure for test_0001"):
        run_reasoner_inference(runtime_config, model_config, manifest)

    assert not (manifest.run_dir / RAW_REASONER_FILENAME).exists()
    partial_path = manifest.run_dir / RAW_REASONER_PARTIAL_FILENAME
    assert partial_path.is_file()
    partial_rows = _read_jsonl(partial_path)
    assert [row["sample_id"] for row in partial_rows] == ["test_0000"]


class RecordingAdapter:
    def __init__(
        self,
        config: ModelConfig,
        fail_sample_id: str | None = None,
        unexpected_fail_sample_id: str | None = None,
    ) -> None:
        self.config = config
        self.fail_sample_id = fail_sample_id
        self.unexpected_fail_sample_id = unexpected_fail_sample_id
        self.load_count = 0
        self.generated_requests: list[ModelGenerationRequest] = []
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
            message="recording adapter not loaded",
        )

    @property
    def load_metadata(self) -> ModelLoadMetadata:
        return self._load_metadata

    def load(self) -> ModelLoadMetadata:
        self.load_count += 1
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
            message="recording adapter loaded",
        )
        return self._load_metadata

    def generate(self, request: ModelGenerationRequest) -> ModelGenerationResult:
        sample_id = _extract_sample_id(request.prompt_text)
        if sample_id == self.unexpected_fail_sample_id:
            raise RuntimeError(f"unexpected failure for {sample_id}")
        if sample_id == self.fail_sample_id:
            raise InferenceError(f"planned failure for {sample_id}")

        self.generated_requests.append(request)
        return ModelGenerationResult(
            raw_text=f"raw output for {sample_id}",
            metadata=ModelGenerationMetadata(
                adapter=self.config.adapter,
                model_name=self.config.model_name,
                max_new_tokens=self.config.max_new_tokens,
                do_sample=self.config.do_sample,
                elapsed_seconds=0.001,
                input_token_count=None,
                output_token_count=None,
                device="cpu",
                torch_dtype=self.config.torch_dtype,
            ),
        )


def _extract_sample_id(prompt_text: str) -> str:
    marker = "Sample ID: "
    start = prompt_text.index(marker) + len(marker)
    return prompt_text[start:].splitlines()[0].strip()
