"""
Clairvoy Video Keyframe Matcher Plugin.

Matches video transcodes and duplicates using stream duration tolerance
and sampled keyframe thumbnail similarity.
"""

from __future__ import annotations

import io
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

from clairvoy.core.format_utils import is_motion_photo_video, is_mpeg_ts
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import BaseMatcherPlugin, DuplicateCluster
from clairvoy.engines.vision_engine import DisjointSetUnion

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".ts",
    ".mp",
}


class VideoKeyframeMatcherPlugin(BaseMatcherPlugin):
    """Matcher plugin that matches video duplicates and transcodes via duration and keyframes."""

    plugin_id: str = "video_matcher"
    display_name: str = "Video Keyframe Matcher (Duration + Keyframe Similarity)"
    version: str = "0.1.0"
    author: str = "Clairvoy Team"
    description: str = "Matches video transcodes and duplicates via stream duration and sampled keyframes"
    match_type: MatchType = MatchType.VISUAL_AI_NEAR_DUPLICATE
    priority_order: int = 30

    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability."""
        if shutil.which("ffprobe"):
            return True, "Video keyframe matcher available (using ffprobe/ffmpeg)."
        if shutil.which("ffmpeg"):
            return True, "Video keyframe matcher available (using ffmpeg)."
        try:
            import cv2

            if cv2 is not None:
                return True, "Video keyframe matcher available (using OpenCV cv2)."
        except (ImportError, Exception):
            pass
        return False, "ffprobe, ffmpeg, or OpenCV cv2 not found in system."

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        """Filter files matching supported video extensions, validating stream headers for ambiguous extensions."""
        supported: list[FileEntry] = []
        for f in files:
            if f.size_bytes <= 0:
                continue
            ext = Path(f.path).suffix.lower()
            if ext not in SUPPORTED_VIDEO_EXTENSIONS:
                continue
            if ext == ".ts" and not is_mpeg_ts(f.path):
                continue
            if ext == ".mp" and not is_motion_photo_video(f.path):
                continue
            supported.append(f)
        return supported

    def extract_duration(self, path: str) -> float | None:
        """Extract media container stream duration in seconds using ffprobe, ffmpeg, or cv2."""
        if not Path(path).is_file():
            return None

        # Method 1: ffprobe
        if shutil.which("ffprobe"):
            try:
                cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    path,
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if res.returncode == 0 and res.stdout.strip():
                    dur = float(res.stdout.strip())
                    if dur > 0:
                        return dur
            except (subprocess.SubprocessError, ValueError, OSError) as exc:
                logger.debug("ffprobe failed to extract duration for %s: %s", path, exc)

        # Method 2: ffmpeg (parse duration from stderr)
        if shutil.which("ffmpeg"):
            try:
                cmd = ["ffmpeg", "-i", path]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stderr)
                if m:
                    hours, minutes, seconds = float(m.group(1)), float(m.group(2)), float(m.group(3))
                    dur = hours * 3600 + minutes * 60 + seconds
                    if dur > 0:
                        return dur
            except (subprocess.SubprocessError, ValueError, OSError) as exc:
                logger.debug("ffmpeg failed to extract duration for %s: %s", path, exc)

        # Method 3: cv2 fallback
        try:
            import cv2

            if cv2 is not None:
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    cap.release()
                    if fps > 0 and frame_count > 0:
                        return float(frame_count / fps)
        except Exception as exc:
            logger.debug("cv2 failed to extract duration for %s: %s", path, exc)

        return None

    def _extract_frame_image(self, path: str, timestamp_sec: float) -> Image.Image | None:
        """Extract a single frame image at a specified timestamp."""
        # Method 1: ffmpeg pipe
        if shutil.which("ffmpeg"):
            try:
                cmd = [
                    "ffmpeg",
                    "-ss",
                    f"{timestamp_sec:.3f}",
                    "-i",
                    path,
                    "-frames:v",
                    "1",
                    "-f",
                    "image2pipe",
                    "-vcodec",
                    "ppm",
                    "-",
                ]
                res = subprocess.run(cmd, capture_output=True, timeout=15)
                if res.returncode == 0 and res.stdout:
                    return Image.open(io.BytesIO(res.stdout))
            except Exception as exc:
                logger.debug("ffmpeg frame extraction failed for %s at %.2fs: %s", path, timestamp_sec, exc)

        # Method 2: cv2 fallback
        try:
            import cv2

            if cv2 is not None:
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000.0)
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        return Image.fromarray(rgb)
        except Exception as exc:
            logger.debug("cv2 frame extraction failed for %s at %.2fs: %s", path, timestamp_sec, exc)

        return None

    @staticmethod
    def compute_image_dhash(img: Image.Image, hash_size: int = 8) -> str:
        """Compute 64-bit difference hash (dHash) from PIL Image."""
        resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
        if hasattr(resized, "get_flattened_data"):
            pixels = list(resized.get_flattened_data())
        else:
            pixels = list(resized.getdata())
        width = hash_size + 1
        bits: list[str] = []
        for row in range(hash_size):
            row_start = row * width
            for col in range(hash_size):
                p1 = pixels[row_start + col]
                p2 = pixels[row_start + col + 1]
                bits.append("1" if p2 > p1 else "0")
        bit_str = "".join(bits)
        return f"{int(bit_str, 2):016x}"

    def extract_keyframe_hashes(
        self,
        path: str,
        duration: float,
        timestamps_pct: tuple[float, ...] = (0.1, 0.5, 0.9),
    ) -> list[str] | None:
        """Extract keyframe perceptual hashes at sampled duration percentages."""
        hashes: list[str] = []
        for pct in timestamps_pct:
            t = max(0.0, min(duration, duration * pct))
            img = self._extract_frame_image(path, t)
            if img is None:
                return None
            hashes.append(self.compute_image_dhash(img))
        return hashes

    @staticmethod
    def is_duration_match(
        d1: float,
        d2: float,
        tolerance_pct: float = 0.015,
        tolerance_abs_sec: float = 1.0,
    ) -> bool:
        """Check if two video durations match within tolerance ±1.5% or ±1.0s."""
        diff = abs(d1 - d2)
        max_d = max(d1, d2)
        if max_d <= 0:
            return False
        return diff <= tolerance_abs_sec or (diff / max_d) <= tolerance_pct

    @staticmethod
    def compare_keyframe_hashes(
        hashes1: list[str],
        hashes2: list[str],
        min_similarity: float = 0.85,
    ) -> tuple[bool, float]:
        """Compare two sets of keyframe hashes.

        Returns (is_match, similarity_score).
        """
        if not hashes1 or not hashes2 or len(hashes1) != len(hashes2):
            return False, 0.0

        if hashes1 == hashes2:
            return True, 1.0

        sims: list[float] = []
        for h1, h2 in zip(hashes1, hashes2, strict=False):
            if h1 == h2:
                sims.append(1.0)
                continue
            try:
                val1 = int(h1, 16)
                val2 = int(h2, 16)
                bit_len = max(len(h1), len(h2), 16) * 4
                dist = bin(val1 ^ val2).count("1")
                sim = max(0.0, 1.0 - (dist / bit_len))
                sims.append(sim)
            except ValueError:
                # Fallback for non-hex mock values
                sims.append(1.0 if h1 == h2 else 0.0)

        avg_sim = sum(sims) / len(sims)
        # Require average similarity >= min_similarity and no single frame < (min_similarity - 0.15)
        if avg_sim >= min_similarity and min(sims) >= (min_similarity - 0.15):
            return True, avg_sim
        return False, avg_sim

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict[str, Any] | None = None,
    ) -> list[DuplicateCluster]:
        """Discover clusters of video duplicates using stream duration and keyframe similarity."""
        is_avail, _ = self.is_available()
        if not is_avail:
            logger.debug("VideoKeyframeMatcherPlugin is not available in the current environment.")
            return []

        ctx = context or {}
        cluster_counter: int = ctx.get("start_cluster_id", 1)
        min_similarity: float = ctx.get("threshold", 0.85)

        supported = self.filter_supported(candidates)
        if len(supported) < 2:
            return []

        # Step 1: Extract durations
        entry_durations: list[tuple[FileEntry, float]] = []
        for entry in supported:
            dur = self.extract_duration(entry.path)
            if dur is not None and dur > 0:
                entry_durations.append((entry, dur))

        if len(entry_durations) < 2:
            return []

        n = len(entry_durations)
        duration_match_pairs: list[tuple[int, int]] = []

        for i in range(n):
            for j in range(i + 1, n):
                d1 = entry_durations[i][1]
                d2 = entry_durations[j][1]
                if self.is_duration_match(d1, d2):
                    duration_match_pairs.append((i, j))

        if not duration_match_pairs:
            return []

        # Step 2: Lazy keyframe extraction and comparison
        keyframe_cache: dict[str, list[str] | None] = {}

        def _get_hashes(entry: FileEntry, dur: float) -> list[str] | None:
            if entry.path not in keyframe_cache:
                keyframe_cache[entry.path] = self.extract_keyframe_hashes(entry.path, dur)
            return keyframe_cache[entry.path]

        dsu = DisjointSetUnion(n)
        pairwise_sims: dict[tuple[int, int], float] = {}

        for i, j in duration_match_pairs:
            entry_i, dur_i = entry_durations[i]
            entry_j, dur_j = entry_durations[j]

            hashes_i = _get_hashes(entry_i, dur_i)
            hashes_j = _get_hashes(entry_j, dur_j)

            if hashes_i is None or hashes_j is None:
                continue

            is_match, sim = self.compare_keyframe_hashes(hashes_i, hashes_j, min_similarity=min_similarity)
            if is_match:
                dsu.union(i, j)
                pairwise_sims[(min(i, j), max(i, j))] = sim

        # Step 3: Group into clusters
        cluster_groups: dict[int, list[int]] = {}
        for idx in range(n):
            root = dsu.find(idx)
            cluster_groups.setdefault(root, []).append(idx)

        clusters: list[DuplicateCluster] = []
        for root, indices in cluster_groups.items():
            if len(indices) < 2:
                continue

            members = [entry_durations[idx][0] for idx in indices]
            durations = [entry_durations[idx][1] for idx in indices]
            avg_duration = sum(durations) / len(durations)

            scores: list[float] = []
            for idx in indices:
                if idx == root:
                    scores.append(1.0)
                else:
                    pair_key = (min(root, idx), max(root, idx))
                    scores.append(pairwise_sims.get(pair_key, 1.0))

            clusters.append(
                DuplicateCluster(
                    cluster_id=cluster_counter,
                    match_type=self.match_type,
                    members=members,
                    similarity_scores=scores,
                    metadata={
                        "duration_seconds": avg_duration,
                        "tolerances": {"pct": 0.015, "abs_sec": 1.0},
                    },
                )
            )
            cluster_counter += 1

        return clusters
