"""Tests for PhotoVisionMatcherPlugin and VisionEngine format expansion (.psd, .heic)."""

import struct
from pathlib import Path

from clairvoy.engines.vision_engine import VisionEngine
from clairvoy.plugins.photo_vision import SUPPORTED_IMAGE_EXTENSIONS


def _make_minimal_psd(w: int = 20, h: int = 20) -> bytes:
    """Generate a minimal valid uncompressed PSD file binary."""
    header = b"8BPS"  # signature
    header += struct.pack(">H", 1)  # version 1
    header += b"\x00" * 6  # reserved
    header += struct.pack(">H", 3)  # channels: 3 (RGB)
    header += struct.pack(">I", h)  # height
    header += struct.pack(">I", w)  # width
    header += struct.pack(">H", 8)  # depth 8 bits
    header += struct.pack(">H", 3)  # mode 3 (RGB)
    header += struct.pack(">I", 0)  # color mode data length
    header += struct.pack(">I", 0)  # image resources length
    header += struct.pack(">I", 0)  # layer and mask length
    header += struct.pack(">H", 0)  # compression 0 (Raw planar)
    raw_pixels = b"\x80" * (w * h * 3)
    return header + raw_pixels


def test_photo_supported_extensions_includes_psd():
    assert ".psd" in SUPPORTED_IMAGE_EXTENSIONS


def test_preprocess_single_image_supports_psd(tmp_path: Path):
    psd_file = tmp_path / "test.psd"
    psd_file.write_bytes(_make_minimal_psd(20, 20))

    tensor, dims = VisionEngine.preprocess_single_image(str(psd_file))
    assert tensor is not None
    assert tensor.shape == (3, 224, 224)
    assert dims == (20, 20)


def test_preprocess_single_image_fallback_heic_or_mock(tmp_path: Path):
    heic_file = tmp_path / "corrupt_photo.heic"
    heic_file.write_bytes(b"\x00" * 50)  # mock invalid file

    # Verify graceful handling of invalid heic without crashing
    tensor, dims = VisionEngine.preprocess_single_image(str(heic_file))
    assert tensor is None
    assert dims == (0, 0)


def test_preprocess_drive_e_heic_if_exists():
    real_heic = Path("/mnt/e/Backup9thOct/D/UsPics/Dhanteras - 2021/IMG_4520.heic")
    if real_heic.is_file():
        tensor, dims = VisionEngine.preprocess_single_image(str(real_heic))
        assert tensor is not None
        assert tensor.shape == (3, 224, 224)
        assert dims[0] > 0 and dims[1] > 0

