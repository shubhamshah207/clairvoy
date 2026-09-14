"""Tests for VideoKeyframeMatcherPlugin expansion to MPEG-TS and Motion Photo formats."""

from pathlib import Path

from clairvoy.core.models import FileEntry
from clairvoy.plugins.video_matcher import SUPPORTED_VIDEO_EXTENSIONS, VideoKeyframeMatcherPlugin


def test_video_supported_extensions_includes_ts_and_mp():
    assert ".ts" in SUPPORTED_VIDEO_EXTENSIONS
    assert ".mp" in SUPPORTED_VIDEO_EXTENSIONS


def test_filter_supported_accepts_valid_mpeg_ts(tmp_path: Path):
    ts_file = tmp_path / "broadcast.ts"
    payload = bytearray(376)
    payload[0] = 0x47
    payload[188] = 0x47
    ts_file.write_bytes(payload)

    plugin = VideoKeyframeMatcherPlugin()
    files = [FileEntry(path=str(ts_file), size_bytes=len(payload))]
    filtered = plugin.filter_supported(files)
    assert len(filtered) == 1
    assert filtered[0].path == str(ts_file)


def test_filter_supported_rejects_typescript_ts(tmp_path: Path):
    ts_file = tmp_path / "index.ts"
    ts_file.write_text("export const hello = 'world';")

    plugin = VideoKeyframeMatcherPlugin()
    files = [FileEntry(path=str(ts_file), size_bytes=30)]
    filtered = plugin.filter_supported(files)
    assert len(filtered) == 0


def test_filter_supported_accepts_motion_photo_mp(tmp_path: Path):
    mp_file = tmp_path / "PXL_20210925.MP"
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    mp_file.write_bytes(header)

    plugin = VideoKeyframeMatcherPlugin()
    files = [FileEntry(path=str(mp_file), size_bytes=len(header))]
    filtered = plugin.filter_supported(files)
    assert len(filtered) == 1
    assert filtered[0].path == str(mp_file)
