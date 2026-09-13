"""
Clairvoy Photo Vision Matcher Plugin.

Local AI visual near-duplicate clustering powered by Meta DINOv2 ONNX.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from clairvoy.core.config import DEFAULT_SIMILARITY_THRESHOLD
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import BaseMatcherPlugin, DuplicateCluster
from clairvoy.engines.vision_engine import HAS_ML, VisionEngine

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
    ".heic",
}


class PhotoVisionMatcherPlugin(BaseMatcherPlugin):
    """Matcher plugin using Meta DINOv2 ONNX embeddings for visual near-duplicate clustering."""

    plugin_id: str = "photo_vision"
    display_name: str = "Photo Vision Matcher (Meta DINOv2)"
    version: str = "0.1.0"
    author: str = "Clairvoy Team"
    description: str = "Local AI visual similarity clustering powered by Meta DINOv2 ONNX"
    match_type: MatchType = MatchType.VISUAL_AI_NEAR_DUPLICATE
    priority_order: int = 20

    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability."""
        if HAS_ML:
            return True, "Meta DINOv2 ONNX vision runtime is available."
        return False, "PIL or onnxruntime is not installed. Vision AI plugin disabled."

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        """Filter files matching supported image extensions or media flag."""
        supported: list[FileEntry] = []
        for f in files:
            if f.size_bytes <= 0:
                continue
            ext = Path(f.path).suffix.lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS or f.is_media:
                supported.append(f)
        return supported

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict[str, Any] | None = None,
    ) -> list[DuplicateCluster]:
        """Discover clusters of near-duplicate images using Meta DINOv2 embeddings."""
        is_avail, _ = self.is_available()
        if not is_avail:
            logger.debug("PhotoVisionMatcherPlugin is not available in the current environment.")
            return []

        ctx = context or {}
        cluster_counter: int = ctx.get("start_cluster_id", 1)
        threshold: float = ctx.get("threshold", DEFAULT_SIMILARITY_THRESHOLD)

        supported_candidates = self.filter_supported(candidates)
        if len(supported_candidates) < 2:
            return []

        candidate_map = {f.path: f for f in supported_candidates}

        engine: VisionEngine | None = ctx.get("vision_engine")
        if engine is None:
            engine = VisionEngine(threshold=threshold)

        raw_clusters = engine.find_near_duplicates([f.path for f in supported_candidates])
        clusters: list[DuplicateCluster] = []

        for group_paths, scores, dims in raw_clusters:
            members = [candidate_map[p] for p in group_paths if p in candidate_map]
            if len(members) < 2:
                continue

            metadata: dict[str, Any] = {
                "threshold": threshold,
                "dimensions": {p: dims[i] for i, p in enumerate(group_paths) if i < len(dims)},
            }

            clusters.append(
                DuplicateCluster(
                    cluster_id=cluster_counter,
                    match_type=self.match_type,
                    members=members,
                    similarity_scores=scores,
                    metadata=metadata,
                )
            )
            cluster_counter += 1

        return clusters
