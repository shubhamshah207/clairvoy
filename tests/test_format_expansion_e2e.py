"""End-to-End Integration tests for expanded media and archive deduplication."""

import struct
import zipfile
from pathlib import Path

from PIL import Image

from clairvoy.engines.pipeline import DeduplicationPipeline


def _make_minimal_psd(w: int = 100, h: int = 100) -> bytes:
    header = b"8BPS"
    header += struct.pack(">H", 1)
    header += b"\x00" * 6
    header += struct.pack(">H", 3)
    header += struct.pack(">I", h)
    header += struct.pack(">I", w)
    header += struct.pack(">H", 8)
    header += struct.pack(">H", 3)
    header += struct.pack(">I", 0)
    header += struct.pack(">I", 0)
    header += struct.pack(">I", 0)
    header += struct.pack(">H", 0)
    raw_pixels = b"\x80" * (w * h * 3)
    return header + raw_pixels


def test_pipeline_cross_format_and_archive_detection(tmp_path: Path):
    # Setup test workspace
    img_jpg = tmp_path / "photo.jpg"
    img = Image.new("RGB", (100, 100), color=(200, 50, 50))
    img.save(img_jpg)

    img_psd = tmp_path / "photo.psd"
    img_psd.write_bytes(_make_minimal_psd(100, 100))

    # JAR archive with member matching on-disk file
    asset_file = tmp_path / "icon.png"
    asset_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)

    jar_file = tmp_path / "bundle.jar"
    with zipfile.ZipFile(jar_file, "w") as zf:
        zf.writestr("assets/icon.png", asset_file.read_bytes())

    # MPEG-TS broadcast video
    ts_file = tmp_path / "stream.ts"
    payload = bytearray(376)
    payload[0] = 0x47
    payload[188] = 0x47
    ts_file.write_bytes(payload)

    # TypeScript source code (should be ignored by video matcher)
    ts_code = tmp_path / "app.ts"
    ts_code.write_text("export const PI = 3.14159;")

    pipeline = DeduplicationPipeline(paths=str(tmp_path))
    summary = pipeline.run_scan()

    assert summary is not None
    # Verify that archive inspection found the duplicate asset in the JAR
    archive_records = [r for r in summary.groups if "::" in r.path]
    assert len(archive_records) >= 1
    assert any("bundle.jar" in r.path for r in archive_records)
