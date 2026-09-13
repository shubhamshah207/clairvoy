"""
Clairvoy Archive Inspector Matcher Plugin.

Peeks inside ZIP and TAR central directories without extracting to disk
to match files against candidates on disk.
"""

from __future__ import annotations

import logging
import tarfile
import zipfile
import zlib
from collections import defaultdict
from typing import Any

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import BaseMatcherPlugin, DuplicateCluster

logger = logging.getLogger(__name__)

ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")


class ArchiveInspectorMatcherPlugin(BaseMatcherPlugin):
    """Matcher plugin that matches on-disk candidate files against archive contents in-memory."""

    plugin_id: str = "archive_inspector"
    display_name: str = "Archive Inspector Matcher (ZIP/TAR Inspection)"
    version: str = "0.1.0"
    author: str = "Clairvoy Team"
    description: str = "Peeks inside ZIP and TAR central directories without extracting to match files on disk"
    match_type: MatchType = MatchType.EXACT_HASH
    priority_order: int = 40

    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability."""
        return True, "ArchiveInspector uses built-in zipfile and tarfile."

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        """Return all valid candidate files."""
        return files

    @staticmethod
    def is_archive(path: str) -> bool:
        """Check if file path has a supported archive extension."""
        return path.lower().endswith(ARCHIVE_SUFFIXES)

    @staticmethod
    def compute_crc32(path: str) -> int | None:
        """Compute CRC32 checksum of an on-disk file in streaming 64KB blocks."""
        try:
            crc = 0
            with open(path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    crc = zlib.crc32(chunk, crc)
            return crc & 0xFFFFFFFF
        except (OSError, PermissionError) as err:
            logger.debug("Failed to compute CRC32 for %s: %s", path, err)
            return None

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict[str, Any] | None = None,
    ) -> list[DuplicateCluster]:
        """Inspect archive central directories and match members with on-disk candidate files.

        Compares candidate size against archive member sizes, then computes CRC32 for candidates
        with matching sizes to verify exact byte duplication without extracting members to disk.
        """
        ctx = context or {}
        cluster_counter: int = ctx.get("start_cluster_id", 1)
        clusters: list[DuplicateCluster] = []

        # Find all archive files across all_indexed_files and candidates
        all_files_dict: dict[str, FileEntry] = {}
        for entry in all_indexed_files or []:
            all_files_dict[entry.path] = entry
        for entry in candidates:
            all_files_dict[entry.path] = entry

        archive_entries = [e for e in all_files_dict.values() if self.is_archive(e.path)]

        if not archive_entries:
            return []

        # Index candidates by file size for O(1) size lookups
        candidates_by_size: dict[int, list[FileEntry]] = defaultdict(list)
        for cand in candidates:
            if cand.size_bytes > 0:
                candidates_by_size[cand.size_bytes].append(cand)

        candidate_crc_cache: dict[str, int | None] = {}

        def _get_candidate_crc(path: str) -> int | None:
            if path not in candidate_crc_cache:
                candidate_crc_cache[path] = self.compute_crc32(path)
            return candidate_crc_cache[path]

        for archive_entry in archive_entries:
            archive_path = archive_entry.path
            lower_path = archive_path.lower()

            # Handle ZIP archives
            if lower_path.endswith(".zip"):
                try:
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        for zinfo in zf.infolist():
                            if zinfo.is_dir() or zinfo.file_size == 0 or zinfo.filename.endswith("/"):
                                continue

                            matching_candidates = candidates_by_size.get(zinfo.file_size, [])
                            for cand in matching_candidates:
                                if cand.path == archive_path:
                                    continue
                                cand_crc = _get_candidate_crc(cand.path)
                                if cand_crc is not None and cand_crc == zinfo.CRC:
                                    clusters.append(
                                        DuplicateCluster(
                                            cluster_id=cluster_counter,
                                            match_type=self.match_type,
                                            members=[
                                                cand,
                                                FileEntry(
                                                    path=f"{archive_path}::{zinfo.filename}",
                                                    size_bytes=zinfo.file_size,
                                                ),
                                            ],
                                            similarity_scores=[1.0, 1.0],
                                            metadata={
                                                "archive": archive_path,
                                                "member": zinfo.filename,
                                                "crc32": zinfo.CRC,
                                            },
                                        )
                                    )
                                    cluster_counter += 1
                except (zipfile.BadZipFile, OSError, PermissionError, EOFError) as err:
                    logger.debug("Skipping invalid or corrupt zip archive %s: %s", archive_path, err)

            # Handle TAR archives
            elif lower_path.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")):
                try:
                    with tarfile.open(archive_path, "r:*") as tf:
                        for member in tf.getmembers():
                            if not member.isfile() or member.size == 0:
                                continue

                            matching_candidates = candidates_by_size.get(member.size, [])
                            if not matching_candidates:
                                continue

                            f_member = tf.extractfile(member)
                            if f_member is None:
                                continue

                            member_crc = 0
                            while chunk := f_member.read(64 * 1024):
                                member_crc = zlib.crc32(chunk, member_crc)
                            member_crc &= 0xFFFFFFFF

                            for cand in matching_candidates:
                                if cand.path == archive_path:
                                    continue
                                cand_crc = _get_candidate_crc(cand.path)
                                if cand_crc is not None and cand_crc == member_crc:
                                    clusters.append(
                                        DuplicateCluster(
                                            cluster_id=cluster_counter,
                                            match_type=self.match_type,
                                            members=[
                                                cand,
                                                FileEntry(
                                                    path=f"{archive_path}::{member.name}",
                                                    size_bytes=member.size,
                                                ),
                                            ],
                                            similarity_scores=[1.0, 1.0],
                                            metadata={
                                                "archive": archive_path,
                                                "member": member.name,
                                                "crc32": member_crc,
                                            },
                                        )
                                    )
                                    cluster_counter += 1
                except (tarfile.TarError, OSError, PermissionError, EOFError) as err:
                    logger.debug("Skipping invalid or corrupt tar archive %s: %s", archive_path, err)

        return clusters
