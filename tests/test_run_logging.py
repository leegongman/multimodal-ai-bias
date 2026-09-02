import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from multimodal_bias.exceptions import ConfigurationError
from multimodal_bias.run_logging import start_run
from multimodal_bias.schemas import CompetitionConfig

FIXED_NOW = datetime(2026, 6, 18, 12, 34, 56, tzinfo=timezone.utc)


def _config(tmp_path: Path, run_name: str = "Baseline Run") -> CompetitionConfig:
    return CompetitionConfig(
        data_root=(tmp_path / "open").resolve(),
        runs_root=tmp_path / "runs",
        run_name=run_name,
    )


def test_start_run_creates_resolved_config_and_environment(tmp_path: Path) -> None:
    config_path = tmp_path / "base.yaml"
    config_path.write_text("run_name: Baseline Run\n", encoding="utf-8")

    manifest = start_run(
        _config(tmp_path),
        config_path=config_path,
        now=FIXED_NOW,
        argv=("multimodal-bias", "start-run"),
    )

    assert manifest.run_id == "20260618_123456_baseline_run"
    assert manifest.run_dir == tmp_path / "runs" / manifest.run_id
    assert manifest.resolved_config_path == manifest.run_dir / "config.resolved.yaml"
    assert manifest.environment_path == manifest.run_dir / "environment.json"

    resolved_config = yaml.safe_load(manifest.resolved_config_path.read_text(encoding="utf-8"))
    assert resolved_config["run_id"] == manifest.run_id
    assert resolved_config["run_dir"] == str(manifest.run_dir.resolve())
    assert resolved_config["config_path"] == str(config_path.resolve())
    assert resolved_config["data_root"] == str((tmp_path / "open").resolve())
    assert resolved_config["runs_root"] == str((tmp_path / "runs").resolve())
    assert resolved_config["run_name"] == "baseline_run"

    environment = json.loads(manifest.environment_path.read_text(encoding="utf-8"))
    assert environment["run_id"] == manifest.run_id
    assert environment["created_at_utc"] == "2026-06-18T12:34:56Z"
    assert environment["argv"] == ["multimodal-bias", "start-run"]
    assert environment["package_version"]
    assert environment["python_version"]
    assert environment["platform"]
    assert environment["executable"]
    assert environment["cwd"]


def test_start_run_adds_stable_suffix_without_overwriting(tmp_path: Path) -> None:
    config = _config(tmp_path, run_name="Experiment")
    config_path = tmp_path / "base.yaml"
    config_path.write_text("run_name: Experiment\n", encoding="utf-8")
    existing_run = tmp_path / "runs" / "20260618_123456_experiment"
    existing_run.mkdir(parents=True)
    marker = existing_run / "marker.txt"
    marker.write_text("do not overwrite", encoding="utf-8")

    first_manifest = start_run(config, config_path=config_path, now=FIXED_NOW)
    second_manifest = start_run(config, config_path=config_path, now=FIXED_NOW)

    assert first_manifest.run_id == "20260618_123456_experiment_001"
    assert second_manifest.run_id == "20260618_123456_experiment_002"
    assert marker.read_text(encoding="utf-8") == "do not overwrite"


@pytest.mark.parametrize("run_name", ["../bad", "bad/name", "café"])
def test_start_run_rejects_unsafe_direct_run_name(tmp_path: Path, run_name: str) -> None:
    config_path = tmp_path / "base.yaml"
    config_path.write_text(f"run_name: {run_name}\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="run_name"):
        start_run(_config(tmp_path, run_name=run_name), config_path=config_path, now=FIXED_NOW)

    assert not (tmp_path / "runs").exists()


def test_start_run_retries_when_directory_creation_races(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path, run_name="Race")
    config_path = tmp_path / "base.yaml"
    config_path.write_text("run_name: Race\n", encoding="utf-8")
    base_name = "20260618_123456_race"
    original_mkdir = Path.mkdir
    state = {"raised": False}

    def racing_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if self.name == base_name and not state["raised"]:
            original_mkdir(self, *args, **kwargs)
            state["raised"] = True
            raise FileExistsError(self)
        original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", racing_mkdir)

    manifest = start_run(config, config_path=config_path, now=FIXED_NOW)

    assert state["raised"] is True
    assert manifest.run_id == "20260618_123456_race_001"


def test_start_run_skips_broken_symlink_run_ids(tmp_path: Path) -> None:
    config = _config(tmp_path, run_name="Symlink")
    config_path = tmp_path / "base.yaml"
    config_path.write_text("run_name: Symlink\n", encoding="utf-8")
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    broken_link = runs_root / "20260618_123456_symlink"
    try:
        broken_link.symlink_to(tmp_path / "missing")
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    manifest = start_run(config, config_path=config_path, now=FIXED_NOW)

    assert manifest.run_id == "20260618_123456_symlink_001"
    assert broken_link.is_symlink()


def test_start_run_removes_partial_run_directory_when_artifact_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "base.yaml"
    config_path.write_text("run_name: Partial\n", encoding="utf-8")
    original_write_text = Path.write_text

    def fail_environment_write(self: Path, *args: object, **kwargs: object) -> int:
        if self.name == "environment.json":
            raise OSError("disk full")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_environment_write)

    with pytest.raises(OSError, match="disk full"):
        start_run(_config(tmp_path, run_name="Partial"), config_path=config_path, now=FIXED_NOW)

    assert list((tmp_path / "runs").iterdir()) == []


def test_start_run_preserves_explicit_empty_argv(tmp_path: Path) -> None:
    config_path = tmp_path / "base.yaml"
    config_path.write_text("run_name: Empty argv\n", encoding="utf-8")

    manifest = start_run(
        _config(tmp_path, run_name="Empty argv"),
        config_path=config_path,
        now=FIXED_NOW,
        argv=(),
    )

    environment = json.loads(manifest.environment_path.read_text(encoding="utf-8"))
    assert environment["argv"] == []
