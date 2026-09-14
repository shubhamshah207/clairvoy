"""Stream signature validation utilities for disambiguating file extensions."""

from __future__ import annotations

from pathlib import Path


def is_mpeg_ts(path: str) -> bool:
    """Return True if the file matches the MPEG-TS packet format (sync byte 0x47).

    Validates that the file has at least 189 bytes and contains the 0x47 sync byte
    at offset 0 and offset 188 (standard 188-byte MPEG transport packet size).
    Instantly filters out TypeScript source code files.
    """
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size < 189:
            return False
        with open(p, "rb") as f:
            chunk = f.read(376)
        if len(chunk) < 189:
            return False
        return chunk[0] == 0x47 and chunk[188] == 0x47
    except (OSError, PermissionError):
        return False


def is_motion_photo_video(path: str) -> bool:
    """Return True if the file contains an ISO Base Media / MP4 container (ftyp box).

    Useful for Google Pixel Motion Photo files named .mp or .MP that store standard
    MP4 video clips.
    """
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size < 16:
            return False
        with open(p, "rb") as f:
            header = f.read(32)
        return b"ftyp" in header[4:16] or (header.startswith(b"\x00\x00\x00") and b"ftyp" in header)
    except (OSError, PermissionError):
        return False


def is_rar_archive(path: str) -> bool:
    """Return True if file starts with the standard RAR archive signature."""
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size < 7:
            return False
        with open(p, "rb") as f:
            magic = f.read(7)
        return magic.startswith(b"Rar!\x1a\x07")
    except (OSError, PermissionError):
        return False
