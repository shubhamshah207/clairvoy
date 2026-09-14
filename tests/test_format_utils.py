"""Unit tests for stream format validation and extension discriminators."""

from pathlib import Path

from clairvoy.core.format_utils import is_motion_photo_video, is_mpeg_ts, is_rar_archive


def test_is_mpeg_ts_valid(tmp_path: Path):
    # MPEG-TS packet sync byte 0x47 every 188 bytes
    ts_file = tmp_path / "stream.ts"
    payload = bytearray(376)
    payload[0] = 0x47
    payload[188] = 0x47
    ts_file.write_bytes(payload)
    assert is_mpeg_ts(str(ts_file)) is True


def test_is_mpeg_ts_rejects_typescript_source(tmp_path: Path):
    ts_file = tmp_path / "app.ts"
    ts_file.write_text("import React from 'react'; export const App = () => null;")
    assert is_mpeg_ts(str(ts_file)) is False


def test_is_mpeg_ts_handles_empty_or_small(tmp_path: Path):
    empty_file = tmp_path / "empty.ts"
    empty_file.write_bytes(b"")
    assert is_mpeg_ts(str(empty_file)) is False


def test_is_motion_photo_video_valid(tmp_path: Path):
    mp_file = tmp_path / "PXL_sample.MP"
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    mp_file.write_bytes(header)
    assert is_motion_photo_video(str(mp_file)) is True


def test_is_motion_photo_video_rejects_non_ftyp(tmp_path: Path):
    txt_file = tmp_path / "readme.mp"
    txt_file.write_text("This is a markdown notes file.")
    assert is_motion_photo_video(str(txt_file)) is False


def test_is_rar_archive_detection(tmp_path: Path):
    rar_file = tmp_path / "archive.rar"
    rar_file.write_bytes(b"Rar!\x1a\x07\x00" + b"\x00" * 20)
    assert is_rar_archive(str(rar_file)) is True

    fake_rar = tmp_path / "fake.rar"
    fake_rar.write_bytes(b"NOT_A_RAR_FILE")
    assert is_rar_archive(str(fake_rar)) is False
