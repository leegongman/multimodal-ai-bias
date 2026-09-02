from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "deploy" / "runpod" / "gemma4-repro"
KNOWN_GOOD_REASONER_V3_SHA256 = (
    "87d694d0b968ccef4606a979f52c5de63454e870be71a6d9f4e91ef942067cb6"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("sample_id", "label"))
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_run(tmp_path: Path, count: int, profile: str = "gemma4-12b") -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rows = [{"sample_id": f"TEST_{index:04d}", "label": str(index % 3)} for index in range(count)]
    write_csv(run_dir / "predictions.csv", rows)
    for name in ("raw_attempts.jsonl", "raw_reasoner.jsonl"):
        (run_dir / name).write_text("{}\n" * count, encoding="utf-8")
    (run_dir / "parsed_reasoner.csv").write_text("sample_id,parse_status\n", encoding="utf-8")
    (run_dir / "run_manifest.json").write_text("{}\n", encoding="utf-8")
    models = {
        "gemma4-12b": (
            "google/gemma-4-12B-it",
            "5926caa4ec0cac5cbfadaf4077420520de1d5205",
        ),
        "gemma4-26b-a4b-awq": (
            "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
            "4033b16200f4152e55e100ea12dc388c537df622",
        ),
    }
    model_id, model_revision = models[profile]
    summary = {
        "sample_count": count,
        "parse_valid_count": count,
        "parse_invalid_count": 0,
        "failure_count": 0,
        "model_name": model_id,
        "model_revision": model_revision,
        "concurrency": 1 if count == 1 else 32,
        "initial_max_tokens": 256,
        "retry_max_tokens": 512,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return run_dir


def test_bundle_contains_proven_server_guards() -> None:
    serve = (BUNDLE / "serve.sh").read_text()
    requirements = (BUNDLE / "requirements-critical.txt").read_text()
    bootstrap = (BUNDLE / "bootstrap.sh").read_text()
    assert "vllm-0.23.0%2Bcu129" in requirements
    assert "fastapi==0.116.1" in requirements
    assert 'PATH="$VENV_DIR/bin:$PATH"' in serve
    assert "/health" in serve and "/v1/models" in serve
    assert "HTTP 500" in serve
    assert "pip-freeze-proven.txt" in bootstrap


def test_validate_run_accepts_complete_subset(tmp_path: Path) -> None:
    module = load_module("validate_run_ok", BUNDLE / "validate_run.py")
    run_dir = build_run(tmp_path, 2)
    module.validate(run_dir, 2, None)


def test_validate_run_accepts_complete_26b_awq_subset(tmp_path: Path) -> None:
    module = load_module("validate_run_26b", BUNDLE / "validate_run.py")
    run_dir = build_run(tmp_path, 2, "gemma4-26b-a4b-awq")
    module.validate(run_dir, 2, None, "gemma4-26b-a4b-awq")


def test_validate_run_rejects_invalid_parse(tmp_path: Path) -> None:
    module = load_module("validate_run_bad", BUNDLE / "validate_run.py")
    run_dir = build_run(tmp_path, 2)
    summary = json.loads((run_dir / "summary.json").read_text())
    summary["parse_valid_count"] = 1
    summary["parse_invalid_count"] = 1
    (run_dir / "summary.json").write_text(json.dumps(summary))
    with pytest.raises(SystemExit, match="parse_valid_count"):
        module.validate(run_dir, 2, None)


def test_validate_bundle_rejects_model_weights(tmp_path: Path) -> None:
    module = load_module("validate_bundle_bad", BUNDLE / "validate_bundle.py")
    (tmp_path / "model.safetensors").write_bytes(b"not a real model")
    with pytest.raises(SystemExit, match="forbidden binary"):
        module.validate(tmp_path)


def test_known_good_reasoner_prompt_is_restored_everywhere() -> None:
    active_prompt = ROOT / "configs" / "prompts" / "reasoner_v3.yaml"
    bundled_prompt = BUNDLE / "runtime" / "configs" / "prompts" / "reasoner_v3.yaml"

    assert sha256_file(active_prompt) == KNOWN_GOOD_REASONER_V3_SHA256
    assert sha256_file(bundled_prompt) == KNOWN_GOOD_REASONER_V3_SHA256
    assert active_prompt.read_bytes() == bundled_prompt.read_bytes()
    for provenance_name in (
        "known-good-runtime.json",
        "known-good-runtime-gemma4-26b-awq.json",
    ):
        provenance = json.loads((BUNDLE / "provenance" / provenance_name).read_text())
        assert provenance["full_run"]["prompt_sha256"] == KNOWN_GOOD_REASONER_V3_SHA256


def test_validate_bundle_rejects_prompt_provenance_mismatch(tmp_path: Path) -> None:
    module = load_module("validate_bundle_prompt_mismatch", BUNDLE / "validate_bundle.py")
    prompt = tmp_path / "runtime" / "configs" / "prompts" / "reasoner_v3.yaml"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("version: reasoner_v3\n", encoding="utf-8")
    provenance = tmp_path / "provenance" / "known-good-runtime.json"
    provenance.parent.mkdir()
    provenance.write_text(
        json.dumps({"full_run": {"prompt_sha256": "a" * 64}}),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="prompt provenance mismatch"):
        module.validate(tmp_path)


def test_full_script_refuses_existing_run_directory() -> None:
    script = (BUNDLE / "run_full.sh").read_text()
    assert '[[ ! -e "$output_dir" ]]' in script
    assert "--concurrency 32" in script
    assert "--initial-max-tokens 256" in script
    assert "--retry-max-tokens 512" in script


def test_bundle_profiles_preserve_12b_and_default_to_proven_26b() -> None:
    env = (BUNDLE / "env.sh").read_text()
    profile_12b = (BUNDLE / "profiles" / "gemma4-12b.sh").read_text()
    profile_26b = (BUNDLE / "profiles" / "gemma4-26b-a4b-awq.sh").read_text()
    assert 'GEMMA_PROFILE="${GEMMA_PROFILE:-gemma4-26b-a4b-awq}"' in env
    assert "google/gemma-4-12B-it" in profile_12b
    assert "5926caa4ec0cac5cbfadaf4077420520de1d5205" in profile_12b
    assert "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit" in profile_26b
    assert "4033b16200f4152e55e100ea12dc388c537df622" in profile_26b
    assert 'VLLM_GENERATION_CONFIG="vllm"' in profile_26b


def test_next_session_prompt_contains_complete_rebuild_handoff() -> None:
    prompt = (BUNDLE / "NEXT_SESSION_PROMPT.md").read_text()
    assert "runpod-gemma4-repro-20260621-gemma26.tar.gz" in prompt
    assert "open.zip" in prompt
    assert "./bootstrap.sh" in prompt
    assert "./download_model.sh" in prompt
    assert "./serve.sh" in prompt
    assert "./smoke.sh" in prompt
    assert "./run_full.sh" in prompt


def test_package_checksum_is_portable() -> None:
    script = (BUNDLE / "package.sh").read_text()
    assert 'shasum -a 256 "$archive_name"' in script
    assert '> "$archive_name.sha256"' in script
