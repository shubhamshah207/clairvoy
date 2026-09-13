"""
Unit tests for Media Matcher Plugins:
- PhotoVisionMatcherPlugin (DINOv2 ONNX)
- VideoKeyframeMatcherPlugin (Duration + Keyframe Similarity)
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import PluginRegistry
from clairvoy.engines.vision_engine import HAS_ML
from clairvoy.plugins.archive_inspector import ArchiveInspectorMatcherPlugin
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin
from clairvoy.plugins.photo_vision import PhotoVisionMatcherPlugin
from clairvoy.plugins.video_matcher import VideoKeyframeMatcherPlugin

# ---------------------------------------------------------------------------
# PhotoVisionMatcherPlugin Tests
# ---------------------------------------------------------------------------


def test_photo_vision_matcher_properties():
    matcher = PhotoVisionMatcherPlugin()
    assert matcher.plugin_id == "photo_vision"
    assert matcher.display_name == "Photo Vision Matcher (Meta DINOv2)"
    assert matcher.version == "0.1.0"
    assert matcher.author == "Clairvoy Team"
    assert "DINOv2" in matcher.description
    assert matcher.match_type == MatchType.VISUAL_AI_NEAR_DUPLICATE
    assert matcher.priority_order == 20

    is_avail, reason = matcher.is_available()
    assert isinstance(is_avail, bool)
    assert isinstance(reason, str)
    if HAS_ML:
        assert is_avail is True


def test_photo_vision_filter_supported(temp_workspace: Path):
    matcher = PhotoVisionMatcherPlugin()

    entries = [
        FileEntry(path="/photos/img1.jpg", size_bytes=1024),
        FileEntry(path="/photos/img2.JPEG", size_bytes=2048),
        FileEntry(path="/photos/img3.png", size_bytes=4096),
        FileEntry(path="/photos/img4.webp", size_bytes=512),
        FileEntry(path="/photos/img5.bmp", size_bytes=10000),
        FileEntry(path="/photos/img6.tiff", size_bytes=20000),
        FileEntry(path="/photos/img7.tif", size_bytes=20000),
        FileEntry(path="/photos/img8.heic", size_bytes=3000),
        FileEntry(path="/photos/document.pdf", size_bytes=1024),
        FileEntry(path="/photos/notes.txt", size_bytes=1024),
        FileEntry(path="/photos/video.mp4", size_bytes=102400),
        FileEntry(path="/photos/empty.jpg", size_bytes=0),
        FileEntry(path="/photos/custom_media.raw", size_bytes=5000, is_media=True),
    ]

    supported = matcher.filter_supported(entries)
    supported_paths = [f.path for f in supported]

    # Verify standard image extensions and is_media entries are included
    assert "/photos/img1.jpg" in supported_paths
    assert "/photos/img2.JPEG" in supported_paths
    assert "/photos/img3.png" in supported_paths
    assert "/photos/img4.webp" in supported_paths
    assert "/photos/img5.bmp" in supported_paths
    assert "/photos/img6.tiff" in supported_paths
    assert "/photos/img7.tif" in supported_paths
    assert "/photos/img8.heic" in supported_paths
    assert "/photos/custom_media.raw" in supported_paths

    # Verify non-images and 0-byte images are excluded
    assert "/photos/document.pdf" not in supported_paths
    assert "/photos/notes.txt" not in supported_paths
    assert "/photos/video.mp4" not in supported_paths
    assert "/photos/empty.jpg" not in supported_paths


@pytest.mark.skipif(not HAS_ML, reason="Meta DINOv2 ONNX dependencies missing")
def test_photo_vision_matcher_plugin(sample_images):
    red1 = str(sample_images["red1"])
    red2 = str(sample_images["red2"])
    blue = str(sample_images["blue"])

    entries = [
        FileEntry(path=red1, size_bytes=Path(red1).stat().st_size),
        FileEntry(path=red2, size_bytes=Path(red2).stat().st_size),
        FileEntry(path=blue, size_bytes=Path(blue).stat().st_size),
    ]

    matcher = PhotoVisionMatcherPlugin()
    clusters = matcher.find_duplicates(
        entries,
        entries,
        context={"threshold": 0.90, "start_cluster_id": 10},
    )

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.cluster_id == 10
    assert cluster.match_type == MatchType.VISUAL_AI_NEAR_DUPLICATE
    assert len(cluster.members) == 2

    member_paths = {m.path for m in cluster.members}
    assert red1 in member_paths
    assert red2 in member_paths
    assert blue not in member_paths

    assert len(cluster.similarity_scores) == 2
    assert all(s >= 0.90 for s in cluster.similarity_scores)
    assert "dimensions" in cluster.metadata


def test_photo_vision_matcher_no_duplicates(temp_workspace: Path):
    p1 = temp_workspace / "color1.png"
    p2 = temp_workspace / "color2.png"
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(p1)
    Image.new("RGB", (100, 100), color=(0, 255, 0)).save(p2)

    entries = [
        FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
        FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
    ]

    matcher = PhotoVisionMatcherPlugin()
    clusters = matcher.find_duplicates(
        entries,
        entries,
        context={"threshold": 0.99},
    )
    assert len(clusters) == 0


def test_photo_vision_matcher_unavailable(monkeypatch):
    matcher = PhotoVisionMatcherPlugin()
    monkeypatch.setattr(matcher, "is_available", lambda: (False, "ML disabled"))

    entries = [
        FileEntry(path="/dummy/a.jpg", size_bytes=100),
        FileEntry(path="/dummy/b.jpg", size_bytes=100),
    ]
    clusters = matcher.find_duplicates(entries, entries, context={})
    assert clusters == []


# ---------------------------------------------------------------------------
# VideoKeyframeMatcherPlugin Tests
# ---------------------------------------------------------------------------


def test_video_matcher_properties():
    matcher = VideoKeyframeMatcherPlugin()
    assert matcher.plugin_id == "video_matcher"
    assert matcher.display_name == "Video Keyframe Matcher (Duration + Keyframe Similarity)"
    assert matcher.version == "0.1.0"
    assert matcher.author == "Clairvoy Team"
    assert "duration" in matcher.description.lower()
    assert matcher.match_type == MatchType.VISUAL_AI_NEAR_DUPLICATE
    assert matcher.priority_order == 30


def test_video_matcher_availability():
    matcher = VideoKeyframeMatcherPlugin()
    is_avail, reason = matcher.is_available()
    assert isinstance(is_avail, bool)
    assert isinstance(reason, str)

    # In our test environment, ffprobe/ffmpeg is available
    if shutil.which("ffprobe") or shutil.which("ffmpeg"):
        assert is_avail is True


def test_video_matcher_availability_missing(monkeypatch):
    matcher = VideoKeyframeMatcherPlugin()
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    monkeypatch.setitem(sys.modules, "cv2", None)

    is_avail, reason = matcher.is_available()
    assert is_avail is False
    assert "not found" in reason.lower() or "missing" in reason.lower() or "unavailable" in reason.lower()


def test_video_matcher_filter_supported():
    matcher = VideoKeyframeMatcherPlugin()

    entries = [
        FileEntry(path="/videos/clip1.mp4", size_bytes=1000),
        FileEntry(path="/videos/clip2.MKV", size_bytes=2000),
        FileEntry(path="/videos/clip3.avi", size_bytes=3000),
        FileEntry(path="/videos/clip4.mov", size_bytes=4000),
        FileEntry(path="/videos/clip5.webm", size_bytes=5000),
        FileEntry(path="/videos/clip6.flv", size_bytes=6000),
        FileEntry(path="/videos/clip7.wmv", size_bytes=7000),
        FileEntry(path="/videos/clip8.m4v", size_bytes=8000),
        FileEntry(path="/videos/photo.jpg", size_bytes=1000),
        FileEntry(path="/videos/doc.txt", size_bytes=100),
        FileEntry(path="/videos/archive.zip", size_bytes=500),
        FileEntry(path="/videos/empty.mp4", size_bytes=0),
    ]

    supported = matcher.filter_supported(entries)
    supported_paths = [f.path for f in supported]

    assert "/videos/clip1.mp4" in supported_paths
    assert "/videos/clip2.MKV" in supported_paths
    assert "/videos/clip3.avi" in supported_paths
    assert "/videos/clip4.mov" in supported_paths
    assert "/videos/clip5.webm" in supported_paths
    assert "/videos/clip6.flv" in supported_paths
    assert "/videos/clip7.wmv" in supported_paths
    assert "/videos/clip8.m4v" in supported_paths

    assert "/videos/photo.jpg" not in supported_paths
    assert "/videos/doc.txt" not in supported_paths
    assert "/videos/archive.zip" not in supported_paths
    assert "/videos/empty.mp4" not in supported_paths


def test_video_matcher_duration_grouping(monkeypatch):
    """Verify duration grouping logic (±1.5% or ±1.0s) and keyframe clustering."""
    matcher = VideoKeyframeMatcherPlugin()

    entries = [
        FileEntry(path="/vids/vid_a.mp4", size_bytes=10_000_000),
        FileEntry(path="/vids/vid_b.mp4", size_bytes=9_000_000),   # Same video transcoded
        FileEntry(path="/vids/vid_c.mp4", size_bytes=10_000_000),  # Same duration, different content
        FileEntry(path="/vids/vid_d.mp4", size_bytes=20_000_000),  # Completely different duration
    ]

    # Durations: vid_a = 60.0s, vid_b = 60.5s (diff 0.5s <= 1.0s, match), vid_c = 60.0s, vid_d = 120.0s
    durations = {
        "/vids/vid_a.mp4": 60.0,
        "/vids/vid_b.mp4": 60.5,
        "/vids/vid_c.mp4": 60.0,
        "/vids/vid_d.mp4": 120.0,
    }

    # Keyframe hashes: vid_a and vid_b match; vid_c differs
    keyframe_hashes = {
        "/vids/vid_a.mp4": ["1111222233334444", "aaaabbbbccccdddd", "5555666677778888"],
        "/vids/vid_b.mp4": ["1111222233334444", "aaaabbbbccccdddd", "5555666677778888"],
        "/vids/vid_c.mp4": ["9999999999999999", "8888888888888888", "7777777777777777"],
        "/vids/vid_d.mp4": ["1111222233334444", "aaaabbbbccccdddd", "5555666677778888"],
    }

    monkeypatch.setattr(matcher, "extract_duration", lambda path: durations.get(path))
    monkeypatch.setattr(
        matcher,
        "extract_keyframe_hashes",
        lambda path, duration: keyframe_hashes.get(path),
    )

    clusters = matcher.find_duplicates(
        entries,
        entries,
        context={"start_cluster_id": 20},
    )

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.cluster_id == 20
    assert cluster.match_type == MatchType.VISUAL_AI_NEAR_DUPLICATE
    assert len(cluster.members) == 2

    paths = {m.path for m in cluster.members}
    assert "/vids/vid_a.mp4" in paths
    assert "/vids/vid_b.mp4" in paths
    assert "/vids/vid_c.mp4" not in paths
    assert "/vids/vid_d.mp4" not in paths


def test_video_matcher_corrupt_files(monkeypatch):
    """Gracefully skip corrupt files without duration or unreadable keyframes."""
    matcher = VideoKeyframeMatcherPlugin()

    entries = [
        FileEntry(path="/vids/corrupt1.mp4", size_bytes=1000),
        FileEntry(path="/vids/corrupt2.mp4", size_bytes=2000),
    ]

    monkeypatch.setattr(matcher, "extract_duration", lambda path: None)

    clusters = matcher.find_duplicates(entries, entries, context={})
    assert clusters == []


@pytest.mark.skipif(
    not shutil.which("ffmpeg"),
    reason="ffmpeg executable not available for synthetic video generation",
)
def test_video_matcher_synthetic_videos(temp_workspace: Path):
    """Generate real synthetic test videos with ffmpeg and verify end-to-end matching."""
    v1 = temp_workspace / "clip1.mp4"
    v2 = temp_workspace / "clip1_copy.mp4"
    v3 = temp_workspace / "clip_different.mp4"

    # Create a 2-second test video (testsrc)
    cmd1 = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "testsrc=duration=2:size=160x120:rate=15",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(v1),
    ]
    subprocess.run(cmd1, capture_output=True, check=True)

    # Transcode clip1 to slightly different bitrate/scale (near-duplicate)
    cmd2 = [
        "ffmpeg", "-y", "-i", str(v1),
        "-vf", "scale=128:96",
        "-c:v", "libx264", "-b:v", "100k",
        str(v2),
    ]
    subprocess.run(cmd2, capture_output=True, check=True)

    # Create a completely different 2-second video (smptebars)
    cmd3 = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "smptebars=duration=2:size=160x120:rate=15",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(v3),
    ]
    subprocess.run(cmd3, capture_output=True, check=True)

    entries = [
        FileEntry(path=str(v1), size_bytes=v1.stat().st_size),
        FileEntry(path=str(v2), size_bytes=v2.stat().st_size),
        FileEntry(path=str(v3), size_bytes=v3.stat().st_size),
    ]

    matcher = VideoKeyframeMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={"start_cluster_id": 1})

    assert len(clusters) == 1
    cluster = clusters[0]
    matched_paths = {m.path for m in cluster.members}
    assert str(v1) in matched_paths
    assert str(v2) in matched_paths
    assert str(v3) not in matched_paths


# ---------------------------------------------------------------------------
# Registry Integration across all 4 Matcher Plugins
# ---------------------------------------------------------------------------


def test_all_plugins_registry_integration():
    """Verify all 4 plugins register and sort properly in ascending priority order:

    ExactHash (10) -> PhotoVision (20) -> VideoKeyframe (30) -> ArchiveInspector (40).
    """
    registry = PluginRegistry()
    exact_hash = ExactHashMatcherPlugin()
    photo_vision = PhotoVisionMatcherPlugin()
    video_matcher = VideoKeyframeMatcherPlugin()
    archive_inspector = ArchiveInspectorMatcherPlugin()

    # Register in non-sorted order to verify sorting by priority_order
    registry.register(archive_inspector)
    registry.register(video_matcher)
    registry.register(exact_hash)
    registry.register(photo_vision)

    matchers = registry.get_matchers()
    assert len(matchers) == 4

    expected_order = [
        ("exact_hash", 10),
        ("photo_vision", 20),
        ("video_matcher", 30),
        ("archive_inspector", 40),
    ]

    for matcher, (expected_id, expected_prio) in zip(matchers, expected_order, strict=True):
        assert matcher.plugin_id == expected_id
        assert matcher.priority_order == expected_prio
