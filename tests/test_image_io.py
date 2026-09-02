from pathlib import Path

from pytest import MonkeyPatch

from multimodal_bias.image_io import load_sample_images
from multimodal_bias.schemas import ImageLoadResult, SampleRecord

JPEG_BYTES = b"\xff\xd8\xff\xe0minimal-jpeg\xff\xd9"
PNG_BYTES = b"\x89PNG\r\n\x1a\nminimal-png"
GIF_BYTES = b"GIF89aminimal-gif"
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBPVP8 "


def _sample_record(sample_id: str, image_path: Path) -> SampleRecord:
    return SampleRecord(
        sample_id=sample_id,
        image_path=image_path.resolve(),
        context="Context",
        question="Question",
        answers=("first", "second", "unknown"),
        row_number=2,
    )


def test_load_sample_images_loads_valid_jpeg_payload(tmp_path: Path) -> None:
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(JPEG_BYTES)
    record = _sample_record("test_0000", image_path)

    report = load_sample_images([record])

    assert report.results == (
        ImageLoadResult(
            sample_id="test_0000",
            image_path=image_path.resolve(),
            status="loaded",
            image_bytes=JPEG_BYTES,
            image_format="jpeg",
            error_message=None,
        ),
    )
    assert report.success_count == 1
    assert report.failure_count == 0


def test_load_sample_images_preserves_input_order(tmp_path: Path) -> None:
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.png"
    first_path.write_bytes(JPEG_BYTES)
    second_path.write_bytes(PNG_BYTES)

    report = load_sample_images(
        [
            _sample_record("test_0001", second_path),
            _sample_record("test_0000", first_path),
        ]
    )

    assert [result.sample_id for result in report.results] == ["test_0001", "test_0000"]
    assert [result.image_format for result in report.results] == ["png", "jpeg"]


def test_load_sample_images_detects_gif_and_webp(tmp_path: Path) -> None:
    gif_path = tmp_path / "image.gif"
    webp_path = tmp_path / "image.webp"
    gif_path.write_bytes(GIF_BYTES)
    webp_path.write_bytes(WEBP_BYTES)

    report = load_sample_images(
        [
            _sample_record("test_0000", gif_path),
            _sample_record("test_0001", webp_path),
        ]
    )

    assert [result.status for result in report.results] == ["loaded", "loaded"]
    assert [result.image_format for result in report.results] == ["gif", "webp"]
    assert report.success_count == 2
    assert report.failure_count == 0


def test_load_sample_images_reports_missing_file(tmp_path: Path) -> None:
    image_path = tmp_path / "missing.jpg"

    report = load_sample_images([_sample_record("test_0000", image_path)])

    result = report.results[0]
    assert result.status == "missing"
    assert result.sample_id == "test_0000"
    assert result.image_path == image_path.resolve()
    assert result.image_bytes is None
    assert result.image_format is None
    assert "does not exist" in (result.error_message or "")
    assert report.success_count == 0
    assert report.failure_count == 1


def test_load_sample_images_reports_unreadable_path_resolution_failure(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    image_path = tmp_path / "unresolvable.jpg"

    def fail_resolve(self: Path) -> Path:
        raise OSError("symlink loop")

    monkeypatch.setattr(Path, "resolve", fail_resolve)

    report = load_sample_images(
        [
            SampleRecord(
                sample_id="test_0000",
                image_path=image_path,
                context="Context",
                question="Question",
                answers=("first", "second", "unknown"),
                row_number=2,
            )
        ]
    )

    result = report.results[0]
    assert result.status == "unreadable"
    assert result.image_path == image_path
    assert result.image_bytes is None
    assert result.image_format is None
    assert "cannot be resolved" in (result.error_message or "")


def test_load_sample_images_reports_unreadable_directory_path(tmp_path: Path) -> None:
    image_path = tmp_path / "image-dir"
    image_path.mkdir()

    report = load_sample_images([_sample_record("test_0000", image_path)])

    result = report.results[0]
    assert result.status == "unreadable"
    assert result.image_bytes is None
    assert result.image_format is None
    assert "not a regular file" in (result.error_message or "")


def test_load_sample_images_reports_unreadable_read_failure(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(JPEG_BYTES)

    def fail_read_bytes(self: Path) -> bytes:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    report = load_sample_images([_sample_record("test_0000", image_path)])

    result = report.results[0]
    assert result.status == "unreadable"
    assert result.image_bytes is None
    assert result.image_format is None
    assert "cannot be read" in (result.error_message or "")


def test_load_sample_images_reports_corrupt_or_empty_file(tmp_path: Path) -> None:
    corrupt_path = tmp_path / "corrupt.jpg"
    empty_path = tmp_path / "empty.jpg"
    corrupt_path.write_bytes(b"not image bytes")
    empty_path.write_bytes(b"")

    report = load_sample_images(
        [
            _sample_record("test_0000", corrupt_path),
            _sample_record("test_0001", empty_path),
        ]
    )

    assert [result.status for result in report.results] == ["corrupt", "corrupt"]
    assert [result.image_bytes for result in report.results] == [None, None]
    assert [result.image_format for result in report.results] == [None, None]
    assert report.success_count == 0
    assert report.failure_count == 2
