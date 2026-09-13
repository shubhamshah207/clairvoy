"""
Clairvoy Exact Hash Matcher Plugin.

High-performance 2-stage hash matching via 128KB QuickHash and full SHA-256.
"""

from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from typing import Any

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import BaseMatcherPlugin, DuplicateCluster

logger = logging.getLogger(__name__)


class ExactHashMatcherPlugin(BaseMatcherPlugin):
    """Matcher plugin using two-stage QuickHash and full SHA-256 content verification."""

    plugin_id: str = "exact_hash"
    display_name: str = "Exact Hash Matcher (QuickHash + SHA-256)"
    version: str = "0.1.0"
    author: str = "Clairvoy Team"
    description: str = "High-performance 2-stage hash matching via 128KB QuickHash and full SHA-256"
    match_type: MatchType = MatchType.EXACT_HASH
    priority_order: int = 10

    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability."""
        return True, "ExactHashMatcher uses built-in hashlib."

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        """Filter out 0-byte files."""
        return [f for f in files if f.size_bytes > 0]

    @staticmethod
    def compute_quick_hash(path: str) -> str | None:
        """Compute preliminary fingerprint from the first 128KB header."""
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                chunk = f.read(128 * 1024)
                h.update(chunk)
            return h.hexdigest()
        except (OSError, PermissionError) as err:
            logger.debug("Failed to compute quick hash for %s: %s", path, err)
            return None

    @staticmethod
    def compute_full_sha256(path: str) -> str | None:
        """Compute complete SHA-256 digest in streaming 64KB blocks."""
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    h.update(chunk)
            return h.hexdigest()
        except (OSError, PermissionError) as err:
            logger.debug("Failed to compute full SHA-256 for %s: %s", path, err)
            return None

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict[str, Any] | None = None,
    ) -> list[DuplicateCluster]:
        """Discover duplicate clusters using size grouping, quick hash, and full SHA-256.

        Stage 1: Group candidates by size_bytes. Skip groups with < 2 files.
        Stage 2: For candidate groups with identical size, compute 128KB quick hash.
                 Group by quick hash and skip groups with < 2 files.
        Stage 3: For candidate groups with identical quick hash, compute full SHA-256.
                 Construct DuplicateCluster for groups with >= 2 matching files.
        """
        ctx = context or {}
        cluster_counter: int = ctx.get("start_cluster_id", 1)
        clusters: list[DuplicateCluster] = []

        # Filter supported (exclude 0-byte files)
        filtered_candidates = self.filter_supported(candidates)

        # Stage 1: Group by file size
        size_groups: dict[int, list[FileEntry]] = defaultdict(list)
        for entry in filtered_candidates:
            size_groups[entry.size_bytes].append(entry)

        for size_bytes, size_group in size_groups.items():
            if len(size_group) < 2:
                continue

            # Stage 2: Group by 128KB QuickHash
            quick_hash_groups: dict[str, list[FileEntry]] = defaultdict(list)
            for entry in size_group:
                if not entry.quick_hash:
                    entry.quick_hash = self.compute_quick_hash(entry.path)
                if entry.quick_hash is not None:
                    quick_hash_groups[entry.quick_hash].append(entry)

            for _qh, qh_group in quick_hash_groups.items():
                if len(qh_group) < 2:
                    continue

                # Stage 3: Group by full SHA-256
                sha_groups: dict[str, list[FileEntry]] = defaultdict(list)
                for entry in qh_group:
                    if not entry.full_sha256:
                        if size_bytes <= 128 * 1024 and entry.quick_hash:
                            entry.full_sha256 = entry.quick_hash
                        else:
                            entry.full_sha256 = self.compute_full_sha256(entry.path)
                    if entry.full_sha256 is not None:
                        sha_groups[entry.full_sha256].append(entry)

                for sha_hash, matching_entries in sha_groups.items():
                    if len(matching_entries) < 2:
                        continue

                    clusters.append(
                        DuplicateCluster(
                            cluster_id=cluster_counter,
                            match_type=self.match_type,
                            members=matching_entries,
                            similarity_scores=[1.0] * len(matching_entries),
                            metadata={"size_bytes": size_bytes, "sha256": sha_hash},
                        )
                    )
                    cluster_counter += 1

        return clusters
