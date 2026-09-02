from pathlib import Path

import pytest

from multimodal_bias.config import load_config
from multimodal_bias.exceptions import ConfigurationError
from multimodal_bias.schemas import CompetitionConfig


def _write_config(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_config_returns_competition_config_with_resolved_paths(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path / "base.yaml",
        """
data_root: data/raw/open
runs_root: runs
run_name: Baseline Run
""".lstrip(),
    )

    config = load_config(config_path)

    assert config == CompetitionConfig(
        data_root=Path("data/raw/open").resolve(),
        runs_root=Path("runs").resolve(),
        run_name="baseline_run",
    )


def test_load_config_fails_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_config(tmp_path / "missing.yaml")


@pytest.mark.parametrize(
    ("content", "match"),
    [
        ("[]\n", "mapping"),
        ("::not yaml:: [\n", "could not be parsed"),
        (
            "1: one\ndata_root: data/raw/open\nruns_root: runs\nrun_name: run\n",
            "keys must be strings",
        ),
        ("data_root: data/raw/open\nruns_root: runs\nrun_name: run\nextra: value\n", "unknown"),
        ("data_root: data/raw/open\nruns_root: runs\nrun_name: ''\n", "run_name"),
        ("data_root: data/raw/open\nruns_root: runs\nrun_name: '../bad'\n", "run_name"),
        ("data_root: data/raw/open\nruns_root: runs\nrun_name: café\n", "run_name"),
    ],
)
def test_load_config_rejects_invalid_contents(tmp_path: Path, content: str, match: str) -> None:
    config_path = _write_config(tmp_path / "bad.yaml", content)

    with pytest.raises(ConfigurationError, match=match):
        load_config(config_path)


def test_load_config_rejects_invalid_config_path() -> None:
    with pytest.raises(ConfigurationError, match="config path is invalid"):
        load_config("bad\0path.yaml")
