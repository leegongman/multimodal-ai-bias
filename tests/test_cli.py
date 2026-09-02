import csv
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from multimodal_bias import __version__
from multimodal_bias.cli import app
from multimodal_bias.exceptions import ModelLoadError, ParseError
from multimodal_bias.parsing import PARSED_REASONER_FIELDNAMES

PNG_BYTES = b"\x89PNG\r\n\x1a\nminimal-png"
ANSI_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _clean_cli_output(output: str) -> str:
    return ANSI_ESCAPE.sub("", output)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_valid_open_layout(tmp_path: Path) -> Path:
    data_root = tmp_path / "open"
    (data_root / "train/images").mkdir(parents=True)
    (data_root / "test/images").mkdir(parents=True)
    (data_root / "train/images/train_img_0000.jpg").write_bytes(PNG_BYTES)
    (data_root / "test/images/test_img_0000.jpg").write_bytes(PNG_BYTES)

    answers = json.dumps(["first person", "second person", "uncertain"])
    _write_csv(
        data_root / "train/train.csv",
        ["sample_id", "image_path", "context", "question", "answers", "label"],
        [
            {
                "sample_id": "train_0000",
                "image_path": "train/images/train_img_0000.jpg",
                "context": "A training context.",
                "question": "Who is described?",
                "answers": answers,
                "label": "0",
            }
        ],
    )
    _write_csv(
        data_root / "test/test.csv",
        ["sample_id", "image_path", "context", "question", "answers"],
        [
            {
                "sample_id": "test_0000",
                "image_path": "test/images/test_img_0000.jpg",
                "context": "A test context.",
                "question": "Who is described?",
                "answers": answers,
            }
        ],
    )
    _write_csv(
        data_root / "sample_submission.csv",
        ["sample_id", "label"],
        [{"sample_id": "test_0000", "label": "0"}],
    )
    return data_root


def _write_runtime_config(path: Path, data_root: Path, runs_root: Path) -> Path:
    path.write_text(
        f"""
data_root: {data_root}
runs_root: {runs_root}
run_name: cli infer
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _write_dummy_model_config(path: Path) -> Path:
    snapshot_path = path.parent / "snapshot"
    snapshot_path.mkdir()
    path.write_text(
        f"""
adapter: dummy
model_name: dummy-vlm
snapshot_path: {snapshot_path}
revision: ""
snapshot_hash: dummy-snapshot
local_files_only: true
trust_remote_code: false
device_map: cpu
torch_dtype: auto
max_new_tokens: 12
do_sample: false
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_valid_parsed_reasoner(path: Path, run_id: str) -> None:
    _write_csv(
        path,
        list(PARSED_REASONER_FIELDNAMES),
        [
            {
                "run_id": run_id,
                "sample_id": "test_0000",
                "parsed_label": "2",
                "uncertainty_option_index": "2",
                "evidence_summary": "The evidence is insufficient.",
                "evidence_type": "insufficient_evidence",
                "uncertainty_signal": "true",
                "risk_flags": "[]",
                "schema_version": "reasoner_output_v3",
                "parse_status": "valid",
                "parse_error": "",
            }
        ],
    )


def _write_triggered_parsed_reasoner(path: Path, run_id: str) -> None:
    _write_csv(
        path,
        list(PARSED_REASONER_FIELDNAMES),
        [
            {
                "run_id": run_id,
                "sample_id": "test_0000",
                "parsed_label": "0",
                "uncertainty_option_index": "2",
                "evidence_summary": "The answer relies on appearance.",
                "evidence_type": "objective_visible_evidence",
                "uncertainty_signal": "false",
                "risk_flags": '["protected_attribute_risk"]',
                "schema_version": "reasoner_output_v3",
                "parse_status": "valid",
                "parse_error": "",
            }
        ],
    )


def _write_verified_artifact(path: Path, run_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "sample_id": "test_0000",
                "prompt_version": "verifier_v1",
                "triggers": ["protected_attribute_risk"],
                "requires_verification": True,
                "before_label": "0",
                "raw_verifier_output": "FINAL_VERIFICATION_JSON: {}",
                "after_label": "1",
                "verifier_reason": "The context explicitly supports answer 1.",
                "verifier_evidence_type": "stated_text_fact",
                "reasoner_defect_found": True,
                "objective_support": True,
                "image_status": "loaded",
                "verifier_parse_status": "valid",
                "generation_metadata": None,
                "model_load_metadata": None,
                "elapsed_seconds": 0.1,
                "status": "verified",
                "error_type": None,
                "error_message": None,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_cli_help_succeeds() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])
    output = _clean_cli_output(result.output + (result.stderr or ""))

    assert result.exit_code == 0
    assert "Usage:" in output
    assert "Multimodal 236722" in output
    assert "--version" in output
    assert "validate-data" in output
    assert "infer" in output
    assert "verify-risky" in output
    assert "make-submission" in output
    assert "shadow-audit" in output
    assert "shadow-freeze" in output
    assert "shadow-evaluate" in output
    assert "shadow-acquire-metadata" in output
    assert "shadow-build-candidate-pool" in output
    assert "Traceback" not in output


def test_cli_no_args_shows_help() -> None:
    runner = CliRunner()

    result = runner.invoke(app)
    output = _clean_cli_output(result.output + (result.stderr or ""))

    assert result.exit_code == 0
    assert "Usage:" in output
    assert "Multimodal 236722" in output


def test_cli_version_succeeds() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])
    output = _clean_cli_output(result.output + (result.stderr or ""))

    assert result.exit_code == 0
    assert output.strip() == f"multimodal-bias {__version__}"


def test_cli_validate_data_succeeds_for_valid_layout(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["validate-data", "--data-root", str(data_root)])

    assert result.exit_code == 0
    assert "Data layout valid" in result.output
    assert "train_rows=1" in result.output
    assert "test_rows=1" in result.output


def test_cli_validate_data_fails_for_invalid_layout(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    (data_root / "test/test.csv").unlink()
    runner = CliRunner()

    result = runner.invoke(app, ["validate-data", "--data-root", str(data_root)])

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Data layout invalid" in combined_output
    assert "test/test.csv" in combined_output
    assert "Traceback" not in combined_output


def test_cli_start_run_creates_run_artifacts(tmp_path: Path) -> None:
    config_path = tmp_path / "base.yaml"
    runs_root = tmp_path / "runs"
    config_path.write_text(
        f"""
data_root: {tmp_path / "open"}
runs_root: {runs_root}
run_name: cli smoke
""".lstrip(),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["start-run", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Run started:" in result.output
    run_dirs = sorted(runs_root.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "config.resolved.yaml").is_file()
    assert (run_dirs[0] / "environment.json").is_file()
    assert "Traceback" not in result.output


def test_cli_start_run_fails_for_invalid_config_without_partial_run(tmp_path: Path) -> None:
    config_path = tmp_path / "base.yaml"
    runs_root = tmp_path / "runs"
    config_path.write_text(
        f"""
data_root: {tmp_path / "open"}
runs_root: {runs_root}
run_name: bad
extra: value
""".lstrip(),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["start-run", "--config", str(config_path)])

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Config invalid" in combined_output
    assert "unknown" in combined_output
    assert "Traceback" not in combined_output
    assert not runs_root.exists()


def test_cli_start_run_fails_without_traceback_when_run_creation_fails(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "base.yaml"
    runs_root = tmp_path / "runs-as-file"
    runs_root.write_text("not a directory", encoding="utf-8")
    config_path.write_text(
        f"""
data_root: {tmp_path / "open"}
runs_root: {runs_root}
run_name: cli failure
""".lstrip(),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["start-run", "--config", str(config_path)])

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Run could not be started" in combined_output
    assert "Traceback" not in combined_output
    assert runs_root.is_file()


def test_cli_smoke_model_succeeds_with_dummy_config(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot"
    snapshot_path.mkdir()
    config_path = tmp_path / "dummy-model.yaml"
    config_path.write_text(
        f"""
adapter: dummy
model_name: dummy-vlm
snapshot_path: {snapshot_path}
revision: ""
snapshot_hash: dummy-snapshot
local_files_only: true
trust_remote_code: false
device_map: cpu
torch_dtype: auto
max_new_tokens: 12
do_sample: false
""".lstrip(),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["smoke-model", "--model-config", str(config_path), "--prompt", "Check local load."],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["load"]["model_name"] == "dummy-vlm"
    assert payload["load"]["load_status"] == "loaded"
    assert payload["load"]["local_files_only"] is True
    assert payload["generation"]["max_new_tokens"] == 12
    assert "Check local load." in payload["raw_text"]
    assert "Traceback" not in result.output


def test_cli_smoke_model_fails_for_invalid_model_config_without_traceback(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "bad-model.yaml"
    config_path.write_text(
        """
adapter: dummy
model_name: dummy-vlm
snapshot_path: snapshot
revision: ""
snapshot_hash: dummy-snapshot
local_files_only: false
trust_remote_code: false
device_map: cpu
torch_dtype: auto
max_new_tokens: 12
do_sample: false
""".lstrip(),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["smoke-model", "--model-config", str(config_path)])

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Model config invalid" in combined_output
    assert "local_files_only" in combined_output
    assert "Traceback" not in combined_output


def test_cli_smoke_model_fails_for_invalid_hf_local_config_without_traceback(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "bad-hf-model.yaml"
    config_path.write_text(
        f"""
adapter: hf_local
model_name: hf-vlm
snapshot_path: {tmp_path / "missing-snapshot"}
revision: abc123
snapshot_hash: ""
local_files_only: true
trust_remote_code: false
device_map: auto
torch_dtype: auto
max_new_tokens: 12
do_sample: false
""".lstrip(),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["smoke-model", "--model-config", str(config_path)])

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Model config invalid" in combined_output
    assert "snapshot_path" in combined_output
    assert "Traceback" not in combined_output


def test_cli_infer_succeeds_with_dummy_model_config(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["infer", "--config", str(runtime_config_path), "--model-config", str(model_config_path)],
    )

    assert result.exit_code == 0
    assert "Inference started:" in result.output
    assert "partial_raw_reasoner_path=" in result.output
    assert "Inference complete:" in result.output
    assert "raw_reasoner_path=" in result.output
    assert "parsed_reasoner_path=" in result.output
    assert "total_samples=1" in result.output
    assert "generated=1" in result.output
    assert "failures=0" in result.output
    assert "parsed_valid=1" in result.output
    assert "parsed_invalid=0" in result.output
    assert "Traceback" not in result.output

    run_dirs = sorted(runs_root.iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / "config.resolved.yaml").is_file()
    assert (run_dir / "environment.json").is_file()
    assert not (run_dir / "raw_reasoner.partial.jsonl").exists()
    raw_rows = _read_jsonl(run_dir / "raw_reasoner.jsonl")
    assert len(raw_rows) == 1
    assert raw_rows[0]["sample_id"] == "test_0000"
    assert raw_rows[0]["status"] == "generated"
    assert raw_rows[0]["raw_output"]
    with (run_dir / "parsed_reasoner.csv").open(encoding="utf-8", newline="") as csv_file:
        parsed_rows = list(csv.DictReader(csv_file))
    assert len(parsed_rows) == 1
    assert parsed_rows[0]["sample_id"] == "test_0000"
    assert parsed_rows[0]["parsed_label"] == "2"
    assert parsed_rows[0]["parse_status"] == "valid"
    for downstream_name in ("final_predictions.csv", "submission.csv"):
        assert not (run_dir / downstream_name).exists()


def test_cli_infer_fails_cleanly_when_reasoner_parser_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")

    def fail_parse(*_args: object, **_kwargs: object) -> object:
        raise ParseError("raw Reasoner artifact has duplicate sample_id")

    monkeypatch.setattr("multimodal_bias.cli.parse_reasoner_artifact", fail_parse)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["infer", "--config", str(runtime_config_path), "--model-config", str(model_config_path)],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Reasoner parsing failed" in combined_output
    assert "duplicate sample_id" in combined_output
    assert "Traceback" not in combined_output
    run_dirs = sorted(runs_root.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "raw_reasoner.jsonl").is_file()
    assert not (run_dirs[0] / "parsed_reasoner.csv").exists()
    assert not (run_dirs[0] / "final_predictions.csv").exists()
    assert not (run_dirs[0] / "submission.csv").exists()


def test_cli_infer_fails_cleanly_when_parsed_artifact_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")

    def fail_parse_write(*_args: object, **_kwargs: object) -> object:
        raise OSError("injected parsed artifact write failure")

    monkeypatch.setattr("multimodal_bias.cli.parse_reasoner_artifact", fail_parse_write)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["infer", "--config", str(runtime_config_path), "--model-config", str(model_config_path)],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Inference artifacts could not be written" in combined_output
    assert "injected parsed artifact write failure" in combined_output
    assert "Traceback" not in combined_output
    run_dirs = sorted(runs_root.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "raw_reasoner.jsonl").is_file()
    assert not (run_dirs[0] / "parsed_reasoner.csv").exists()


def test_cli_infer_fails_for_invalid_config_without_traceback(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "infer",
            "--config",
            str(tmp_path / "missing-config.yaml"),
            "--model-config",
            str(tmp_path / "missing-model.yaml"),
        ],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Config invalid" in combined_output
    assert "Traceback" not in combined_output


def test_cli_infer_fails_for_invalid_model_config_without_traceback(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runtime_config_path = _write_runtime_config(
        tmp_path / "base.yaml", data_root, tmp_path / "runs"
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "infer",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(tmp_path / "missing-model.yaml"),
        ],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Model config invalid" in combined_output
    assert "Traceback" not in combined_output


def test_cli_infer_fails_for_invalid_prompt_template_without_traceback(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")
    bad_prompt_path = tmp_path / "bad-prompt.yaml"
    bad_prompt_path.write_text("version: bad\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "infer",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(model_config_path),
            "--prompt-template",
            str(bad_prompt_path),
        ],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Inference config invalid" in combined_output
    assert "prompt template missing required keys" in combined_output
    assert "Traceback" not in combined_output
    assert not runs_root.exists()


def test_cli_infer_fails_for_model_load_error_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")

    def fail_prepare(*_args: object, **_kwargs: object) -> object:
        raise ModelLoadError("offline model snapshot could not be loaded")

    monkeypatch.setattr("multimodal_bias.cli.prepare_reasoner_inference", fail_prepare)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["infer", "--config", str(runtime_config_path), "--model-config", str(model_config_path)],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Model load failed" in combined_output
    assert "offline model snapshot could not be loaded" in combined_output
    assert "Traceback" not in combined_output
    assert not runs_root.exists()


def test_cli_infer_fails_for_invalid_data_layout_without_traceback(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    runtime_config_path = _write_runtime_config(
        tmp_path / "base.yaml",
        tmp_path / "missing-open",
        runs_root,
    )
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["infer", "--config", str(runtime_config_path), "--model-config", str(model_config_path)],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Data layout invalid" in combined_output
    assert "Traceback" not in combined_output
    assert not runs_root.exists()


def test_cli_make_submission_writes_validated_run_artifacts(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260618_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_valid_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["make-submission", "--config", str(runtime_config_path), "--run-id", run_id],
    )

    assert result.exit_code == 0
    assert "Submission complete:" in result.output
    assert f"run_id={run_id}" in result.output
    assert "final_predictions_path=" in result.output
    assert "submission_path=" in result.output
    assert "total_samples=1" in result.output
    assert "Traceback" not in result.output
    with (run_dir / "submission.csv").open(encoding="utf-8", newline="") as csv_file:
        assert list(csv.DictReader(csv_file)) == [{"sample_id": "test_0000", "label": "2"}]
    assert (run_dir / "final_predictions.csv").is_file()


def test_cli_make_submission_fences_v3_from_legacy_verification(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260618_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_triggered_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    _write_verified_artifact(run_dir / "verification.jsonl", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "make-submission",
            "--config",
            str(runtime_config_path),
            "--run-id",
            run_id,
            "--use-verification",
        ],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "legacy arbitration is not compatible" in combined_output
    assert not (run_dir / "submission.csv").exists()
    assert not (run_dir / "final_predictions.csv").exists()


def test_cli_make_submission_with_verification_rejects_missing_artifact_without_outputs(
    tmp_path: Path,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260618_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_triggered_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "make-submission",
            "--config",
            str(runtime_config_path),
            "--run-id",
            run_id,
            "--use-verification",
        ],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Submission invalid" in combined_output
    assert "verification.jsonl" in combined_output
    assert "Traceback" not in combined_output
    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()


def test_cli_make_submission_rejects_run_id_path_escape_without_traceback(
    tmp_path: Path,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["make-submission", "--config", str(runtime_config_path), "--run-id", "../outside"],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Submission invalid" in combined_output
    assert "run_id" in combined_output
    assert "Traceback" not in combined_output


@pytest.mark.parametrize(
    "run_id",
    ["/absolute", "nested/run", "nested\\run", ".", "..", "missing-run"],
)
def test_cli_make_submission_rejects_unsafe_or_missing_run_ids_without_traceback(
    tmp_path: Path,
    run_id: str,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["make-submission", "--config", str(runtime_config_path), "--run-id", run_id],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Submission invalid" in combined_output
    assert "Traceback" not in combined_output


def test_cli_make_submission_rejects_invalid_parsed_row_without_outputs(
    tmp_path: Path,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260618_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_valid_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    parsed_path = run_dir / "parsed_reasoner.csv"
    parsed_path.write_text(
        parsed_path.read_text(encoding="utf-8").replace(",valid,", ",invalid_json,"),
        encoding="utf-8",
    )
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["make-submission", "--config", str(runtime_config_path), "--run-id", run_id],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Submission invalid" in combined_output
    assert "parse_status" in combined_output
    assert "Traceback" not in combined_output
    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()


def test_cli_make_submission_maps_write_failure_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260618_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_valid_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)

    def fail_generation(*_args: object, **_kwargs: object) -> object:
        raise OSError("injected final artifact write failure")

    monkeypatch.setattr("multimodal_bias.cli.generate_submission_artifacts", fail_generation)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["make-submission", "--config", str(runtime_config_path), "--run-id", run_id],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Submission artifacts could not be written" in combined_output
    assert "injected final artifact write failure" in combined_output
    assert "Traceback" not in combined_output


def test_cli_make_submission_maps_data_layout_failure_without_traceback(
    tmp_path: Path,
) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    (data_root / "sample_submission.csv").unlink()
    runs_root = tmp_path / "runs"
    run_id = "20260618_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_valid_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["make-submission", "--config", str(runtime_config_path), "--run-id", run_id],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Data layout invalid" in combined_output
    assert "sample_submission.csv" in combined_output
    assert "Traceback" not in combined_output
    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()


def test_cli_verify_risky_fences_triggered_v3_record(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260619_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_triggered_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "verify-risky",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(model_config_path),
            "--run-id",
            run_id,
        ],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "legacy Verifier is not compatible" in combined_output
    assert not (run_dir / "verification.jsonl").exists()
    assert not (run_dir / "final_predictions.csv").exists()
    assert not (run_dir / "submission.csv").exists()


def test_cli_verify_risky_fences_non_triggered_v3_record(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260619_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_valid_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "verify-risky",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(model_config_path),
            "--run-id",
            run_id,
        ],
    )

    combined_output = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "legacy Verifier is not compatible" in combined_output
    assert not (run_dir / "verification.jsonl").exists()


def test_cli_verify_risky_rejects_unsafe_run_id_without_traceback(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "verify-risky",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(model_config_path),
            "--run-id",
            "../outside",
        ],
    )

    combined = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Verification invalid" in combined
    assert "Traceback" not in combined


def test_cli_verify_risky_requires_run_id() -> None:
    result = CliRunner().invoke(app, ["verify-risky"])
    output = _clean_cli_output(result.output + (result.stderr or ""))

    assert result.exit_code == 2
    assert "--run-id" in output


def test_cli_verify_risky_rejects_malformed_parsed_artifact(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260619_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "parsed_reasoner.csv").write_text("bad,headers\n1,2\n", encoding="utf-8")
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")

    result = CliRunner().invoke(
        app,
        [
            "verify-risky",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(model_config_path),
            "--run-id",
            run_id,
        ],
    )

    combined = result.output + (result.stderr or "")
    assert result.exit_code == 1
    assert "Verification invalid" in combined
    assert "headers" in combined
    assert not (run_dir / "verification.jsonl").exists()


def test_cli_verify_risky_rejects_invalid_prompt_and_existing_output(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260619_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_triggered_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)
    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")
    bad_prompt = tmp_path / "bad-verifier.yaml"
    bad_prompt.write_text("version: bad\n", encoding="utf-8")

    invalid_prompt_result = CliRunner().invoke(
        app,
        [
            "verify-risky",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(model_config_path),
            "--prompt-template",
            str(bad_prompt),
            "--run-id",
            run_id,
        ],
    )
    assert invalid_prompt_result.exit_code == 1
    assert "legacy Verifier is not compatible" in (
        invalid_prompt_result.output + (invalid_prompt_result.stderr or "")
    )

    output = run_dir / "verification.jsonl"
    output.write_text("existing\n", encoding="utf-8")
    existing_result = CliRunner().invoke(
        app,
        [
            "verify-risky",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(model_config_path),
            "--run-id",
            run_id,
        ],
    )
    assert existing_result.exit_code == 1
    assert "legacy Verifier is not compatible" in (
        existing_result.output + (existing_result.stderr or "")
    )
    assert output.read_text(encoding="utf-8") == "existing\n"


def test_cli_verify_risky_maps_invalid_model_and_data_without_traceback(tmp_path: Path) -> None:
    data_root = _build_valid_open_layout(tmp_path)
    runs_root = tmp_path / "runs"
    run_id = "20260619_120000_candidate"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    _write_triggered_parsed_reasoner(run_dir / "parsed_reasoner.csv", run_id)
    runtime_config_path = _write_runtime_config(tmp_path / "base.yaml", data_root, runs_root)

    invalid_model_result = CliRunner().invoke(
        app,
        [
            "verify-risky",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(tmp_path / "missing-model.yaml"),
            "--run-id",
            run_id,
        ],
    )
    invalid_model_output = invalid_model_result.output + (invalid_model_result.stderr or "")
    assert invalid_model_result.exit_code == 1
    assert "Verification config invalid" in invalid_model_output
    assert "Traceback" not in invalid_model_output

    model_config_path = _write_dummy_model_config(tmp_path / "dummy-model.yaml")
    (data_root / "sample_submission.csv").unlink()
    invalid_data_result = CliRunner().invoke(
        app,
        [
            "verify-risky",
            "--config",
            str(runtime_config_path),
            "--model-config",
            str(model_config_path),
            "--run-id",
            run_id,
        ],
    )
    invalid_data_output = invalid_data_result.output + (invalid_data_result.stderr or "")
    assert invalid_data_result.exit_code == 1
    assert "Data layout invalid" in invalid_data_output
    assert "Traceback" not in invalid_data_output


def test_installed_console_script_help_version_and_validate_data_succeed(tmp_path: Path) -> None:
    script_path = shutil.which("multimodal-bias")
    assert script_path is not None
    data_root = _build_valid_open_layout(tmp_path)

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    help_result = subprocess.run(
        [script_path, "--help"],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    assert help_result.returncode == 0
    help_output = _clean_cli_output(help_result.stdout + help_result.stderr)
    assert "Usage:" in help_output
    assert "Multimodal 236722" in help_output
    assert "--version" in help_output

    version_result = subprocess.run(
        [script_path, "--version"],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    assert version_result.returncode == 0
    version_output = _clean_cli_output(version_result.stdout + version_result.stderr)
    assert version_output.strip() == f"multimodal-bias {__version__}"

    validate_result = subprocess.run(
        [script_path, "validate-data", "--data-root", str(data_root)],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    assert validate_result.returncode == 0
    validate_output = _clean_cli_output(validate_result.stdout + validate_result.stderr)
    assert "Data layout valid" in validate_output
