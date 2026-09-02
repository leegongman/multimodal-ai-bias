"""Image IO boundary for local multimodal inference inputs."""

from collections.abc import Iterable

from multimodal_bias.schemas import (
    ImageFormat,
    ImageLoadReport,
    ImageLoadResult,
    SampleRecord,
)


def load_sample_images(records: Iterable[SampleRecord]) -> ImageLoadReport:
    """Load image bytes for parsed samples while preserving input order."""

    return ImageLoadReport(results=tuple(_load_one_image(record) for record in records))


def _load_one_image(record: SampleRecord) -> ImageLoadResult:
    try:
        image_path = record.image_path.resolve()
    except (OSError, RuntimeError) as exc:
        return ImageLoadResult(
            sample_id=record.sample_id,
            image_path=record.image_path,
            status="unreadable",
            image_bytes=None,
            image_format=None,
            error_message=f"image path cannot be resolved: {exc}",
        )

    if not image_path.exists():
        return ImageLoadResult(
            sample_id=record.sample_id,
            image_path=image_path,
            status="missing",
            image_bytes=None,
            image_format=None,
            error_message=f"image path does not exist: {image_path}",
        )

    if not image_path.is_file():
        return ImageLoadResult(
            sample_id=record.sample_id,
            image_path=image_path,
            status="unreadable",
            image_bytes=None,
            image_format=None,
            error_message=f"image path is not a regular file: {image_path}",
        )

    try:
        image_bytes = image_path.read_bytes()
    except OSError as exc:
        return ImageLoadResult(
            sample_id=record.sample_id,
            image_path=image_path,
            status="unreadable",
            image_bytes=None,
            image_format=None,
            error_message=f"image file cannot be read: {exc}",
        )

    if not image_bytes:
        return ImageLoadResult(
            sample_id=record.sample_id,
            image_path=image_path,
            status="corrupt",
            image_bytes=None,
            image_format=None,
            error_message=f"image file is empty: {image_path}",
        )

    image_format = _detect_image_format(image_bytes)
    if image_format is None:
        return ImageLoadResult(
            sample_id=record.sample_id,
            image_path=image_path,
            status="corrupt",
            image_bytes=None,
            image_format=None,
            error_message=f"unsupported or corrupt image bytes: {image_path}",
        )

    return ImageLoadResult(
        sample_id=record.sample_id,
        image_path=image_path,
        status="loaded",
        image_bytes=image_bytes,
        image_format=image_format,
        error_message=None,
    )


def _detect_image_format(image_bytes: bytes) -> ImageFormat | None:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "webp"
    return None
