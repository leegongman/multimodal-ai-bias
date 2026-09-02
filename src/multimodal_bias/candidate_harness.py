"""Candidate eligibility and real-image adapter smoke boundary."""

from __future__ import annotations

import importlib
import json
import os
import re
import tempfile
import zlib
from dataclasses import asdict, is_dataclass
from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import yaml

from multimodal_bias.exceptions import CandidateEligibilityError
from multimodal_bias.image_io import load_sample_images
from multimodal_bias.models.adapter import VisionLanguageModelAdapter, create_model_adapter
from multimodal_bias.parsing import parse_reasoner_output
from multimodal_bias.prompting.templates import build_reasoner_prompt
from multimodal_bias.schemas import (
    CandidateHardwareTelemetry,
    CandidateManifest,
    CandidateRejection,
    CandidateRenderedInputEvidence,
    CandidateSmokeReport,
    ModelConfig,
    ModelGenerationRequest,
    ModelLoadMetadata,
    SampleRecord,
)

CANDIDATE_CUTOFF = date(2026, 5, 31)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
RELEASE_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
A6000_NAME_PATTERN = re.compile(r"^(?:NVIDIA\s+)?RTX\s+A6000$", re.IGNORECASE)
CANDIDATE_MANIFEST_KEYS = frozenset(
    {
        "candidate_id",
        "official_repo",
        "commit",
        "release_date",
        "cutoff_evidence",
        "license_id",
        "license_url",
        "snapshot_sha256",
        "custom_code_hashes",
        "dependency_lock_path",
        "processor_evidence",
        "chat_template_evidence",
        "image_serialization_evidence",
        "preprocessing_metadata",
        "remote_api_usage",
    }
)


class _UniqueLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _unique_mapping(loader: _UniqueLoader, node: yaml.MappingNode, deep: bool = False):
    loader.flatten_mapping(node)
    pairs = loader.construct_pairs(node, deep=deep)
    result: dict[object, object] = {}
    for key, value in pairs:
        try:
            duplicate = key in result
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "mapping keys must be hashable",
                node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key {key!r}",
                node.start_mark,
            )
        result[key] = value
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_candidate_manifest(path: Path | str) -> CandidateManifest:
    """Load a strict, offline candidate eligibility manifest."""

    manifest_path = Path(path)
    try:
        raw = yaml.load(manifest_path.read_text(encoding="utf-8"), Loader=_UniqueLoader)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise CandidateEligibilityError("manifest_invalid", str(exc)) from exc
    if not isinstance(raw, dict) or any(not isinstance(key, str) for key in raw):
        raise CandidateEligibilityError("manifest_invalid", "manifest must be a string-key mapping")
    if set(raw) != CANDIDATE_MANIFEST_KEYS:
        raise CandidateEligibilityError("manifest_invalid", "manifest fields must match exactly")

    commit = _text(raw, "commit")
    if not COMMIT_PATTERN.fullmatch(commit):
        raise CandidateEligibilityError("commit_unpinned", "commit must be 40 lowercase hex")
    release_date_text = _text(raw, "release_date")
    if not RELEASE_DATE_PATTERN.fullmatch(release_date_text):
        raise CandidateEligibilityError(
            "manifest_invalid", "release_date must be canonical YYYY-MM-DD"
        )
    try:
        release_date = date.fromisoformat(release_date_text)
    except ValueError as exc:
        raise CandidateEligibilityError(
            "manifest_invalid", "release_date must be YYYY-MM-DD"
        ) from exc
    if release_date > CANDIDATE_CUTOFF:
        raise CandidateEligibilityError("cutoff_ineligible", release_date_text)
    if raw["remote_api_usage"] != "none":
        raise CandidateEligibilityError("remote_api_forbidden", "remote_api_usage must be none")
    snapshot_hash = _text(raw, "snapshot_sha256")
    if not SHA256_PATTERN.fullmatch(snapshot_hash):
        raise CandidateEligibilityError(
            "snapshot_hash_invalid", "snapshot_sha256 must be lowercase hex"
        )

    custom_hashes = _string_mapping(raw["custom_code_hashes"], "custom_code_hashes")
    if any(not SHA256_PATTERN.fullmatch(value) for _, value in custom_hashes):
        raise CandidateEligibilityError(
            "custom_code_hash_invalid", "custom code hashes must be SHA-256"
        )
    _verify_custom_code_hashes(manifest_path.parent, custom_hashes)
    preprocessing = _string_mapping(raw["preprocessing_metadata"], "preprocessing_metadata")
    if not preprocessing:
        raise CandidateEligibilityError(
            "serialization_evidence_missing", "preprocessing metadata is empty"
        )
    serialization_evidence = {
        key: _serialization_evidence(raw, key)
        for key in (
            "processor_evidence",
            "chat_template_evidence",
            "image_serialization_evidence",
        )
    }
    lock_path = _resolve_evidence_file(
        manifest_path.parent,
        _text(raw, "dependency_lock_path"),
        missing_code="dependency_lock_missing",
    )

    return CandidateManifest(
        candidate_id=_text(raw, "candidate_id"),
        official_repo=_text(raw, "official_repo"),
        commit=commit,
        release_date=release_date_text,
        cutoff_evidence=_text(raw, "cutoff_evidence"),
        license_id=_text(raw, "license_id"),
        license_url=_text(raw, "license_url"),
        snapshot_sha256=snapshot_hash,
        custom_code_hashes=custom_hashes,
        dependency_lock_path=lock_path,
        processor_evidence=serialization_evidence["processor_evidence"],
        chat_template_evidence=serialization_evidence["chat_template_evidence"],
        image_serialization_evidence=serialization_evidence["image_serialization_evidence"],
        preprocessing_metadata=preprocessing,
        remote_api_usage="none",
    )


def run_candidate_smoke(
    manifest: CandidateManifest,
    model_config: ModelConfig,
    image_path: Path | str,
    *,
    adapter: VisionLanguageModelAdapter | None = None,
    hardware: CandidateHardwareTelemetry | None = None,
) -> CandidateSmokeReport:
    """Run one offline, real-image Reasoner v3 smoke and all promotion gates."""

    rejections: list[CandidateRejection] = []
    if adapter is None and model_config.adapter == "dummy":
        rejections.append(
            CandidateRejection("adapter_ineligible", "dummy adapter cannot enter diagnostic-48")
        )
    if not model_config.local_files_only:
        rejections.append(
            CandidateRejection("remote_api_forbidden", "local_files_only must be true")
        )
    if model_config.snapshot_hash != manifest.snapshot_sha256:
        rejections.append(CandidateRejection("snapshot_hash_mismatch", "model config differs"))
    if model_config.revision and model_config.revision != manifest.commit:
        rejections.append(CandidateRejection("commit_mismatch", "model config differs"))
    if model_config.trust_remote_code and not manifest.custom_code_hashes:
        rejections.append(
            CandidateRejection(
                "custom_code_evidence_missing",
                "trust_remote_code requires verified custom-code hashes",
            )
        )
    if rejections:
        return _report(manifest, hardware or _detect_hardware(), rejections)

    sample = SampleRecord(
        sample_id="candidate_smoke",
        image_path=Path(image_path),
        context="No identity-relevant fact is provided.",
        question="Which answer is objectively supported?",
        answers=("First option", "Second option", "Cannot be determined"),
        row_number=1,
    )
    image = load_sample_images((sample,)).results[0]
    if image.status != "loaded" or image.image_bytes is None:
        rejections.append(CandidateRejection("image_invalid", image.error_message or image.status))
        return _report(manifest, hardware or _detect_hardware(), rejections)
    image_error = _image_decode_error(image.image_bytes)
    if image_error is not None:
        rejections.append(CandidateRejection("image_invalid", image_error))
        return _report(manifest, hardware or _detect_hardware(), rejections)

    prompt = build_reasoner_prompt(sample)
    prompt_text = f"{prompt.system_prompt}\n\n{prompt.user_prompt}"
    rendered = CandidateRenderedInputEvidence(
        prompt.prompt_version,
        sha256(prompt_text.encode()).hexdigest(),
        sha256(image.image_bytes).hexdigest(),
        manifest.processor_evidence,
        manifest.chat_template_evidence,
        manifest.image_serialization_evidence,
        manifest.preprocessing_metadata,
    )
    runtime = None
    load_metadata: ModelLoadMetadata | None = None
    generation = None
    raw_output = None
    parsed = None
    try:
        runtime = adapter or create_model_adapter(model_config)
        load_metadata = runtime.load()
    except Exception as exc:
        rejections.append(CandidateRejection("offline_load_failed", str(exc)))
    if not isinstance(load_metadata, ModelLoadMetadata):
        if not any(item.code == "offline_load_failed" for item in rejections):
            rejections.append(
                CandidateRejection("offline_load_failed", "adapter returned no load metadata")
            )
    elif load_metadata.load_status != "loaded":
        rejections.append(
            CandidateRejection("offline_load_failed", load_metadata.message or "load failed")
        )
    elif not _load_identity_matches(load_metadata, model_config, manifest):
        rejections.append(
            CandidateRejection("load_identity_mismatch", "loaded model identity differs")
        )
    if load_metadata is not None and load_metadata.load_status == "loaded" and not rejections:
        try:
            _reset_peak_memory()
            assert runtime is not None
            result = runtime.generate(
                ModelGenerationRequest(
                    prompt_text=prompt_text,
                    image_path=image.image_path,
                    image_bytes=image.image_bytes,
                    image_format=image.image_format,
                )
            )
            generation, raw_output = result.metadata, result.raw_text
            parsed = parse_reasoner_output(
                raw_output, run_id="candidate_smoke", sample_id=sample.sample_id
            )
            if parsed.parse_status != "valid":
                rejections.append(
                    CandidateRejection("structured_output_invalid", parsed.parse_error or "invalid")
                )
        except Exception as exc:
            rejections.append(CandidateRejection("generation_failed", str(exc)))
    telemetry = hardware or _detect_hardware()
    if not _is_a6000(telemetry.gpu_name):
        rejections.append(CandidateRejection("gpu_not_a6000", str(telemetry.gpu_name)))
    if telemetry.total_vram_mib is None or telemetry.total_vram_mib < 48000:
        rejections.append(CandidateRejection("vram_insufficient", str(telemetry.total_vram_mib)))
    if telemetry.peak_vram_mib is None or telemetry.peak_vram_mib < 0:
        rejections.append(CandidateRejection("peak_vram_missing", str(telemetry.peak_vram_mib)))
    if generation is None or raw_output is None or parsed is None:
        if not any(
            item.code in {"offline_load_failed", "load_identity_mismatch", "generation_failed"}
            for item in rejections
        ):
            rejections.append(
                CandidateRejection("adapter_contract_invalid", "generation evidence is incomplete")
            )
    return CandidateSmokeReport(
        manifest.candidate_id,
        manifest,
        load_metadata,
        generation,
        rendered,
        telemetry,
        raw_output,
        parsed.parsed_label if parsed else None,
        parsed.uncertainty_option_index if parsed else None,
        parsed.schema_version if parsed else None,
        generation.elapsed_seconds if generation else None,
        tuple(rejections),
        not rejections,
    )


def write_candidate_report(report: CandidateSmokeReport, output_path: Path | str) -> Path:
    """Atomically publish deterministic candidate smoke JSON without clobbering."""

    path = Path(output_path)
    temp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temp = Path(handle.name)
            json.dump(
                _jsonable(report), handle, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            handle.write("\n")
        os.link(temp, path)
    except FileExistsError as exc:
        if path.exists():
            raise CandidateEligibilityError(
                "report_exists", f"candidate report already exists: {path}"
            ) from exc
        raise CandidateEligibilityError("report_write_failed", str(exc)) from exc
    except (OSError, UnicodeError, ValueError) as exc:
        raise CandidateEligibilityError("report_write_failed", str(exc)) from exc
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return path


def _report(
    manifest: CandidateManifest,
    hardware: CandidateHardwareTelemetry,
    rejections: list[CandidateRejection],
) -> CandidateSmokeReport:
    return CandidateSmokeReport(
        manifest.candidate_id,
        manifest,
        None,
        None,
        None,
        hardware,
        None,
        None,
        None,
        None,
        None,
        tuple(rejections),
        False,
    )


def _detect_hardware() -> CandidateHardwareTelemetry:
    try:
        torch = importlib.import_module("torch")
        if not torch.cuda.is_available():
            return CandidateHardwareTelemetry(None, None, None)
        props = torch.cuda.get_device_properties(0)
        return CandidateHardwareTelemetry(
            props.name,
            int(props.total_memory / 1024**2),
            int(torch.cuda.max_memory_allocated(0) / 1024**2),
        )
    except (ImportError, RuntimeError, AttributeError):
        return CandidateHardwareTelemetry(None, None, None)


def _reset_peak_memory() -> None:
    try:
        torch = importlib.import_module("torch")
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats(0)
    except (ImportError, RuntimeError, AttributeError):
        return


def _text(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CandidateEligibilityError("manifest_invalid", f"{key} must be non-empty text")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CandidateEligibilityError("manifest_invalid", f"{key} is not UTF-8") from exc
    return value.strip()


def _serialization_evidence(raw: dict[str, Any], key: str) -> str:
    try:
        return _text(raw, key)
    except CandidateEligibilityError as exc:
        raise CandidateEligibilityError(
            "serialization_evidence_missing", f"{key} must be non-empty text"
        ) from exc


def _string_mapping(value: object, key: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict):
        raise CandidateEligibilityError("manifest_invalid", f"{key} must be a string mapping")
    normalized: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            raise CandidateEligibilityError("manifest_invalid", f"{key} must be a string mapping")
        normalized_key = raw_key.strip()
        normalized_value = raw_value.strip()
        if not normalized_key or not normalized_value:
            raise CandidateEligibilityError("manifest_invalid", f"{key} must be a string mapping")
        try:
            normalized_key.encode("utf-8")
            normalized_value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise CandidateEligibilityError(
                "manifest_invalid", f"{key} must contain UTF-8 text"
            ) from exc
        if normalized_key in normalized:
            raise CandidateEligibilityError(
                "manifest_invalid", f"{key} contains duplicate normalized keys"
            )
        normalized[normalized_key] = normalized_value
    return tuple(sorted(normalized.items()))


def _resolve_evidence_file(base: Path, value: str, *, missing_code: str) -> Path:
    try:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = base / path
        path = path.resolve()
        if not path.is_file():
            raise CandidateEligibilityError(missing_code, str(path))
    except CandidateEligibilityError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise CandidateEligibilityError(missing_code, f"{value}: {exc}") from exc
    return path


def _verify_custom_code_hashes(base: Path, custom_hashes: tuple[tuple[str, str], ...]) -> None:
    for path_text, expected_hash in custom_hashes:
        path = _resolve_evidence_file(base, path_text, missing_code="custom_code_missing")
        digest = sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise CandidateEligibilityError("custom_code_missing", f"{path}: {exc}") from exc
        if digest.hexdigest() != expected_hash:
            raise CandidateEligibilityError("custom_code_hash_mismatch", str(path))


def _image_decode_error(image_bytes: bytes) -> str | None:
    try:
        image_module = importlib.import_module("PIL.Image")
    except ImportError:
        return _image_structure_error(image_bytes)
    try:
        with image_module.open(BytesIO(image_bytes)) as image:
            image.verify()
    except (OSError, SyntaxError, ValueError) as exc:
        return f"image decode failed: {exc}"
    return None


def _image_structure_error(image_bytes: bytes) -> str | None:
    """Reject truncated/corrupt image containers when Pillow is unavailable."""

    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        offset = 8
        seen_ihdr = False
        seen_idat = False
        seen_iend = False
        compressed_pixels = bytearray()
        while offset + 12 <= len(image_bytes):
            length = int.from_bytes(image_bytes[offset : offset + 4], "big")
            chunk_end = offset + 12 + length
            if length > len(image_bytes) or chunk_end > len(image_bytes):
                return "image decode failed: truncated PNG chunk"
            chunk_type = image_bytes[offset + 4 : offset + 8]
            chunk_data = image_bytes[offset + 8 : offset + 8 + length]
            expected_crc = int.from_bytes(image_bytes[offset + 8 + length : chunk_end], "big")
            if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != expected_crc:
                return "image decode failed: invalid PNG checksum"
            if chunk_type == b"IHDR":
                if seen_ihdr or length != 13:
                    return "image decode failed: invalid PNG header"
                width = int.from_bytes(chunk_data[:4], "big")
                height = int.from_bytes(chunk_data[4:8], "big")
                if width < 1 or height < 1:
                    return "image decode failed: invalid PNG dimensions"
                seen_ihdr = True
            elif chunk_type == b"IDAT":
                seen_idat = True
                compressed_pixels.extend(chunk_data)
            elif chunk_type == b"IEND":
                if length != 0:
                    return "image decode failed: invalid PNG end marker"
                seen_iend = True
                offset = chunk_end
                break
            offset = chunk_end
        if not (seen_ihdr and seen_idat and seen_iend) or offset != len(image_bytes):
            return "image decode failed: incomplete PNG"
        try:
            zlib.decompress(compressed_pixels)
        except zlib.error as exc:
            return f"image decode failed: invalid PNG pixel data: {exc}"
        return None
    if image_bytes.startswith(b"\xff\xd8\xff"):
        if len(image_bytes) < 8 or not image_bytes.endswith(b"\xff\xd9"):
            return "image decode failed: incomplete JPEG"
        return None
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        if len(image_bytes) < 14 or image_bytes[-1:] != b";":
            return "image decode failed: incomplete GIF"
        return None
    if len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        declared_size = int.from_bytes(image_bytes[4:8], "little") + 8
        if declared_size != len(image_bytes) or len(image_bytes) < 20:
            return "image decode failed: incomplete WEBP"
        return None
    return "image decode failed: unsupported image container"


def _load_identity_matches(
    metadata: ModelLoadMetadata,
    config: ModelConfig,
    manifest: CandidateManifest,
) -> bool:
    if (
        metadata.model_name != config.model_name
        or metadata.adapter != config.adapter
        or metadata.snapshot_path != config.snapshot_path
        or metadata.snapshot_hash != manifest.snapshot_sha256
        or not metadata.local_files_only
        or metadata.trust_remote_code != config.trust_remote_code
    ):
        return False
    if config.revision and metadata.revision != manifest.commit:
        return False
    if metadata.revision and metadata.revision != manifest.commit:
        return False
    return True


def _is_a6000(gpu_name: str | None) -> bool:
    if gpu_name is None:
        return False
    return bool(A6000_NAME_PATTERN.fullmatch(" ".join(gpu_name.split())))


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
