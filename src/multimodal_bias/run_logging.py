"""Run logging boundary."""

from __future__ import annotations

import json
import platform
import shutil
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

import yaml

from multimodal_bias import __version__
from multimodal_bias.run_names import normalize_run_name
from multimodal_bias.schemas import CompetitionConfig, RunManifest


def start_run(
    config: CompetitionConfig,
    config_path: Path | str,
    *,
    now: datetime | None = None,
    argv: Sequence[str] | None = None,
) -> RunManifest:
    """Create a unique run directory with reproducibility artifacts."""

    created_at = _coerce_utc(now or datetime.now(timezone.utc))
    run_name = normalize_run_name(config.run_name, source="config run_name")
    source_config_path = _resolve_source_config_path(config_path)
    run_id, run_dir = _create_run_directory(created_at, run_name, config.runs_root)

    resolved_config_path = run_dir / "config.resolved.yaml"
    environment_path = run_dir / "environment.json"
    try:
        resolved_config = {
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "config_path": str(source_config_path),
            "data_root": str(config.data_root.resolve()),
            "runs_root": str(config.runs_root.resolve()),
            "run_name": run_name,
        }
        environment = {
            "argv": list(sys.argv if argv is None else argv),
            "created_at_utc": _format_utc(created_at),
            "cwd": str(Path.cwd()),
            "executable": sys.executable,
            "package_version": __version__,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "run_id": run_id,
        }

        resolved_config_path.write_text(
            yaml.safe_dump(resolved_config, sort_keys=True),
            encoding="utf-8",
        )
        environment_path.write_text(
            json.dumps(environment, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise

    return RunManifest(
        run_id=run_id,
        run_dir=run_dir,
        config_path=source_config_path,
        resolved_config_path=resolved_config_path,
        environment_path=environment_path,
        created_at_utc=_format_utc(created_at),
    )


def _resolve_source_config_path(config_path: Path | str) -> Path:
    try:
        return Path(config_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise OSError(f"source config path is invalid: {config_path}: {exc}") from exc


def _create_run_directory(created_at: datetime, run_name: str, runs_root: Path) -> tuple[str, Path]:
    while True:
        run_id = _create_run_id(created_at, run_name, runs_root)
        run_dir = runs_root / run_id
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_id, run_dir


def _create_run_id(created_at: datetime, run_name: str, runs_root: Path) -> str:
    base_run_id = f"{created_at:%Y%m%d_%H%M%S}_{run_name}"
    candidate = base_run_id
    suffix = 1
    candidate_path = runs_root / candidate
    while candidate_path.exists() or candidate_path.is_symlink():
        candidate = f"{base_run_id}_{suffix:03d}"
        suffix += 1
        candidate_path = runs_root / candidate
    return candidate


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
