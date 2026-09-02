import base64
import csv
import hashlib
import io
import json
from email.message import Message
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from multimodal_bias.exceptions import ShadowValidationError
from multimodal_bias.shadow_acquisition import (
    ACQUISITION_SCHEMA,
    acquire_shadow_metadata,
    build_shadow_candidate_pool,
    download_shadow_candidate_images,
    generate_pending_shadow_records,
    load_source_manifest,
)


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self._offset = 0
        self.headers = Message()
        self.headers["Content-Type"] = "text/csv"
        self.headers["ETag"] = '"fixture"'

    def read(self, size: int) -> bytes:
        chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def close(self) -> None:
        pass


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_acquisition(root: Path) -> Path:
    raw = root / "raw"
    raw.mkdir(parents=True)
    miap_fields = [
        "ImageID",
        "XMin",
        "XMax",
        "YMin",
        "YMax",
        "IsGroupOf",
        "IsDepictionOf",
        "GenderPresentation",
        "AgePresentation",
    ]
    miap_rows = []
    for image_index in range(4):
        for person_index in range(2):
            miap_rows.append(
                {
                    "ImageID": f"oi-{image_index}",
                    "XMin": 0.1 + person_index * 0.4,
                    "XMax": 0.35 + person_index * 0.4,
                    "YMin": 0.1,
                    "YMax": 0.8,
                    "IsGroupOf": 0,
                    "IsDepictionOf": 0,
                    "GenderPresentation": "SensitiveValue",
                    "AgePresentation": "SensitiveValue",
                }
            )
    miap = raw / "miap.csv"
    _write_csv(miap, miap_fields, miap_rows)

    attribution_fields = [
        "ImageID",
        "OriginalURL",
        "OriginalLandingURL",
        "License",
        "Author",
        "Title",
        "OriginalMD5",
        "Rotation",
    ]
    attribution = raw / "attribution.csv"
    _write_csv(
        attribution,
        attribution_fields,
        [
            {
                "ImageID": f"oi-{index}",
                "OriginalURL": f"https://images.example/{index}.jpg",
                "OriginalLandingURL": f"https://flickr.example/{index}",
                "License": "https://creativecommons.org/licenses/by/2.0/",
                "Author": f"author-{index}",
                "Title": f"title-{index}",
                "OriginalMD5": f"md5-{index}",
                "Rotation": "0",
            }
            for index in range(4)
        ],
    )
    vsr = raw / "vsr-train.jsonl"
    vsr.write_text(
        "".join(
            json.dumps(
                {
                    "image": f"vsr-{index}.jpg",
                    "image_link": f"http://images.cocodataset.org/{index}.jpg",
                    "caption": "The person is behind the bicycle.",
                    "label": index % 2,
                    "relation": "behind",
                }
            )
            + "\n"
            for index in range(3)
        ),
        encoding="utf-8",
    )
    sources = [
        ("miap", "miap_boxes", miap),
        ("attribution", "openimages_attribution", attribution),
        ("vsr", "vsr", vsr),
    ]
    manifest = {
        "schema_version": ACQUISITION_SCHEMA,
        "pixel_files_downloaded": 0,
        "source_manifest_sha256": "",
        "sources": [
            {
                "id": source_id,
                "kind": kind,
                "filename": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for source_id, kind, path in sources
        ],
    }
    source_manifest = root / "source-manifest.yaml"
    source_manifest.write_text("version: fixture\n", encoding="utf-8")
    manifest["source_manifest_sha256"] = hashlib.sha256(source_manifest.read_bytes()).hexdigest()
    (root / "acquisition.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_source_manifest_rejects_non_allowlisted_url(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        f"""version: {ACQUISITION_SCHEMA}
sources:
  - id: bad
    kind: vsr
    filename: data.jsonl
    url: https://example.com/data.jsonl
""",
        encoding="utf-8",
    )

    with pytest.raises(ShadowValidationError, match="allowlisted"):
        load_source_manifest(manifest)


def test_acquisition_is_hashed_no_clobber_and_metadata_only(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        f"""version: {ACQUISITION_SCHEMA}
sources:
  - id: source-a
    kind: vsr
    filename: source.jsonl
    url: https://huggingface.co/source.jsonl
""",
        encoding="utf-8",
    )
    body = b'{"image":"one.jpg"}\n'

    result = acquire_shadow_metadata(
        manifest, tmp_path / "out", opener=lambda *_a, **_k: _Response(body)
    )

    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["pixel_files_downloaded"] == 0
    assert payload["sources"][0]["bytes"] == len(body)
    assert (tmp_path / "out/raw/source.jsonl").read_bytes() == body
    with pytest.raises(ShadowValidationError, match="overwrite"):
        acquire_shadow_metadata(
            manifest, tmp_path / "out", opener=lambda *_a, **_k: _Response(body)
        )


def test_acquisition_cleans_partial_directory_on_failure(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        f"""version: {ACQUISITION_SCHEMA}
sources:
  - id: source-a
    kind: vsr
    filename: source.jsonl
    url: https://huggingface.co/source.jsonl
""",
        encoding="utf-8",
    )

    def fail(*_args: object, **_kwargs: object) -> object:
        raise OSError("network down")

    with pytest.raises(ShadowValidationError, match="network down"):
        acquire_shadow_metadata(manifest, tmp_path / "out", opener=fail)
    assert not (tmp_path / "out.partial").exists()


def test_candidate_pool_is_deterministic_and_strips_sensitive_fields(tmp_path: Path) -> None:
    acquisition = _write_acquisition(tmp_path / "acquisition")

    first = build_shadow_candidate_pool(
        acquisition, tmp_path / "pool-a", open_images_count=3, vsr_count=2
    )
    build_shadow_candidate_pool(acquisition, tmp_path / "pool-b", open_images_count=3, vsr_count=2)

    assert json.loads(first.read_text())["candidate_count"] == 5
    first_rows = (tmp_path / "pool-a/candidates.jsonl").read_text(encoding="utf-8")
    second_rows = (tmp_path / "pool-b/candidates.jsonl").read_text(encoding="utf-8")
    assert first_rows == second_rows
    assert "SensitiveValue" not in first_rows
    assert "GenderPresentation" not in first_rows
    assert "AgePresentation" not in first_rows
    assert not list((tmp_path / "pool-a").glob("*.jpg"))


def test_candidate_pool_reports_and_excludes_degenerate_miap_boxes(tmp_path: Path) -> None:
    acquisition = _write_acquisition(tmp_path / "acquisition")
    miap = acquisition / "raw/miap.csv"
    with miap.open("a", encoding="utf-8") as stream:
        stream.write("bad,0.1,0.2,1.0,1.0,0,0,Unknown,Unknown\n")
    manifest = json.loads((acquisition / "acquisition.json").read_text())
    manifest["sources"][0]["sha256"] = hashlib.sha256(miap.read_bytes()).hexdigest()
    (acquisition / "acquisition.json").write_text(json.dumps(manifest), encoding="utf-8")

    report_path = build_shadow_candidate_pool(
        acquisition, tmp_path / "pool", open_images_count=3, vsr_count=2
    )

    report = json.loads(report_path.read_text())
    assert report["miap_filter_counts"]["excluded_invalid_geometry_rows"] == 1


def test_candidate_pool_rejects_mutated_source(tmp_path: Path) -> None:
    acquisition = _write_acquisition(tmp_path / "acquisition")
    (acquisition / "raw/miap.csv").write_text("mutated", encoding="utf-8")

    with pytest.raises(ShadowValidationError, match="hash mismatch"):
        build_shadow_candidate_pool(
            acquisition, tmp_path / "pool", open_images_count=3, vsr_count=2
        )


def _jpeg_fixture(index: int) -> bytes:
    image = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20 + index * 50, 20, 120 + index * 60, 250), fill="black")
    stream = io.BytesIO()
    image.save(stream, format="JPEG", quality=90)
    return stream.getvalue()


def test_image_download_verifies_license_md5_decode_and_hashes(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    images = {f"https://images.example/{index}.jpg": _jpeg_fixture(index) for index in range(3)}
    rows = []
    for index, (url, body) in enumerate(images.items()):
        rows.append(
            {
                "source_dataset": "open_images_miap",
                "source_id": f"oi-{index}",
                "image_pixel_url": url,
                "image_landing_url": f"https://flickr.example/{index}",
                "license_url": "https://creativecommons.org/licenses/by/2.0/",
                "creator": f"author-{index}",
                "title": f"title-{index}",
                "source_checksum_md5_base64": base64.b64encode(
                    hashlib.md5(body, usedforsecurity=False).digest()
                ).decode(),
                "person_count": 2,
                "person_boxes": [],
            }
        )
    candidates.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def fetch(url: str, _limit: int) -> tuple[bytes, dict[str, str]]:
        if url in images:
            return images[url], {"Content-Type": "image/jpeg"}
        return b"https://creativecommons.org/licenses/by/2.0/", {"Content-Type": "text/html"}

    report_path = download_shadow_candidate_images(
        candidates, tmp_path / "images", count=2, concurrency=2, fetcher=fetch
    )

    report = json.loads(report_path.read_text())
    assert report["accepted_count"] == 2
    assert report["review_status"] == "pending_human_safety_and_content_review"
    image_files = list((tmp_path / "images/images").iterdir())
    assert len(image_files) == 2
    with Image.open(image_files[0]) as decoded:
        assert decoded.size == (400, 300)
    with pytest.raises(ShadowValidationError, match="overwrite"):
        download_shadow_candidate_images(candidates, tmp_path / "images", count=2, fetcher=fetch)


def test_image_download_rejects_missing_license_page(tmp_path: Path) -> None:
    body = _jpeg_fixture(0)
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(
        json.dumps(
            {
                "source_dataset": "open_images_miap",
                "source_id": "oi-0",
                "image_pixel_url": "https://images.example/0.jpg",
                "image_landing_url": "https://flickr.example/0",
                "license_url": "https://creativecommons.org/licenses/by/2.0/",
                "creator": "author",
                "title": "title",
                "source_checksum_md5_base64": base64.b64encode(
                    hashlib.md5(body, usedforsecurity=False).digest()
                ).decode(),
                "person_count": 2,
                "person_boxes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def fetch(url: str, _limit: int) -> tuple[bytes, dict[str, str]]:
        if "images.example" in url:
            return body, {"Content-Type": "image/jpeg"}
        return b"license unavailable", {"Content-Type": "text/html"}

    with pytest.raises(ShadowValidationError, match="only 0 images passed"):
        download_shadow_candidate_images(candidates, tmp_path / "images", count=1, fetcher=fetch)
    assert not (tmp_path / "images.partial").exists()


def test_pending_generation_is_exactly_balanced_and_unreviewed(tmp_path: Path) -> None:
    manifest = tmp_path / "images.jsonl"
    manifest.write_text(
        "".join(
            json.dumps(
                {
                    "source_id": f"oi-{index}",
                    "sha256": f"{index:064x}",
                    "local_path": f"images/{index:064x}.jpg",
                    "image_landing_url": f"https://flickr.example/{index}",
                    "license_url": "https://creativecommons.org/licenses/by/2.0/",
                    "creator": f"author-{index}",
                    "title": f"title-{index}",
                }
            )
            + "\n"
            for index in range(600)
        ),
        encoding="utf-8",
    )

    report_path = generate_pending_shadow_records(manifest, tmp_path / "pending")

    report = json.loads(report_path.read_text())
    assert report["record_count"] == 600
    assert report["reviewed_count"] == 0
    assert report["selection_count"] == 420
    assert report["sealed_holdout_count"] == 180
    assert report["ambiguous_count"] == 120
    assert report["resolvable_count"] == 480
    assert report["label_counts"] == {"0": 200, "1": 200, "2": 200}
    assert report["uncertainty_position_counts"] == {"0": 200, "1": 200, "2": 200}
    rows = [
        json.loads(line) for line in (tmp_path / "pending/records.jsonl").read_text().splitlines()
    ]
    assert all(row["review_status"] == "pending" for row in rows)
    assert all(row["provenance_type"] == "generated_allowed" for row in rows)
