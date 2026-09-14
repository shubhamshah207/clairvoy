"""
Clairvoy Document Text & Tabular Matcher Plugin.

Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt,
.csv, and .tsv files using normalized text representations, tabular row sorting,
token Jaccard similarity, and Disjoint Set Union (DSU) clustering.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import BaseMatcherPlugin, DuplicateCluster

logger = logging.getLogger(__name__)

try:
    import pypdf

    HAS_PYPDF = True
    PYPDF_VERSION = getattr(pypdf, "__version__", "unknown")
except ImportError:
    HAS_PYPDF = False
    PYPDF_VERSION = None

SUPPORTED_DOCUMENT_EXTENSIONS: set[str] = {
    ".pdf",
    ".docx",
    ".pptx",
    ".odt",
    ".csv",
    ".tsv",
}

MAX_BUFFER_BYTES = 25 * 1024 * 1024  # 25 MB file/stream cap
MAX_WORDS = 50_000  # Cap extracted text at 50,000 words
MAX_PDF_PAGES = 50  # Cap PDF inspection to first 50 pages
SIMILARITY_THRESHOLD = 0.90  # Token Jaccard threshold for near-duplicates
MIN_TOKENS_FOR_SIMILARITY = 5  # Minimum tokens required for near-duplicate matching


class DisjointSetUnion:
    """Disjoint Set Union (DSU) with path compression and union by rank."""

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, i: int) -> int:
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int) -> bool:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.rank[root_i] < self.rank[root_j]:
                self.parent[root_i] = root_j
            elif self.rank[root_i] > self.rank[root_j]:
                self.parent[root_j] = root_i
            else:
                self.parent[root_j] = root_i
                self.rank[root_i] += 1
            return True
        return False


class DocumentTextMatcherPlugin(BaseMatcherPlugin):
    """Matcher plugin for content-aware document and tabular deduplication."""

    plugin_id: str = "document_matcher"
    display_name: str = "Document Text & Tabular Matcher"
    version: str = "0.1.0"
    author: str = "Clairvoy Team"
    description: str = "Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv"
    match_type: MatchType = MatchType.CONTENT_NEAR_DUPLICATE
    priority_order: int = 50

    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability."""
        if HAS_PYPDF:
            return True, f"pypdf {PYPDF_VERSION} available"
        return False, "pypdf not installed. Please install pypdf>=5.0.0"

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        """Filter candidates by supported document extensions and non-zero size."""
        return [
            entry
            for entry in files
            if entry.size_bytes > 0
            and Path(entry.path).suffix.lower() in SUPPORTED_DOCUMENT_EXTENSIONS
        ]

    def extract_document_representation(
        self, path: str
    ) -> tuple[str, str, int] | None:
        """Extract canonical document representation: (content_hash, preview, length)."""
        data = self._extract_document_data(path)
        if data is None:
            return None
        content_hash, preview, length, _ = data
        return content_hash, preview, length

    def _extract_document_data(
        self, path: str
    ) -> tuple[str, str, int, set[str]] | None:
        """Extract content hash, preview snippet, length, and token set."""
        ext = Path(path).suffix.lower()
        if ext not in SUPPORTED_DOCUMENT_EXTENSIONS:
            return None

        if not os.path.isfile(path):
            return None

        try:
            if ext == ".pdf":
                raw_text = self._extract_pdf_text(path)
            elif ext == ".docx":
                raw_text = self._extract_docx_text(path)
            elif ext == ".pptx":
                raw_text = self._extract_pptx_text(path)
            elif ext == ".odt":
                raw_text = self._extract_odt_text(path)
            elif ext in {".csv", ".tsv"}:
                raw_text = self._extract_tabular_text(path)
            else:
                return None
        except Exception as e:
            logger.debug("Extraction error on %s: %s", path, e)
            return None

        if not raw_text:
            return None

        # Normalize whitespace and apply word cap
        if ext in {".csv", ".tsv"}:
            # Tabular data is already structured; apply word cap if excessive
            words = raw_text.split()
            if not words:
                return None
            norm_text = " ".join(words[:MAX_WORDS]) if len(words) > MAX_WORDS else raw_text
        else:

            norm_text = re.sub(r"\s+", " ", raw_text).strip()
            if not norm_text:
                return None
            words = norm_text.split()
            if len(words) > MAX_WORDS:
                norm_text = " ".join(words[:MAX_WORDS])

        content_hash = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
        preview = norm_text[:500]
        length = len(norm_text)
        tokens = set(re.findall(r"\b\w+\b", norm_text.lower()))

        return content_hash, preview, length, tokens

    def _extract_pdf_text(self, path: str) -> str | None:
        """Extract text from PDF using pure-Python pypdf up to 50 pages."""
        if not HAS_PYPDF:
            return None

        try:
            reader = pypdf.PdfReader(path)
            if getattr(reader, "is_encrypted", False):
                try:
                    if not reader.decrypt(""):
                        return None
                except Exception:
                    return None

            pages = reader.pages[:MAX_PDF_PAGES]
            text_parts: list[str] = []
            total_bytes = 0

            for page in pages:
                page_text = page.extract_text() or ""
                if page_text:
                    text_parts.append(page_text)
                    total_bytes += len(page_text.encode("utf-8", errors="replace"))
                    if total_bytes >= MAX_BUFFER_BYTES:
                        break

            joined = " ".join(text_parts).strip()
            return joined if joined else None
        except Exception as e:
            logger.debug("Failed to extract PDF text from %s: %s", path, e)
            return None

    def _extract_docx_text(self, path: str) -> str | None:
        """Extract body text from .docx by inspecting word/document.xml in memory."""
        try:
            with zipfile.ZipFile(path, "r") as zf:
                if "word/document.xml" not in zf.namelist():
                    return None
                with zf.open("word/document.xml") as f:
                    xml_content = f.read(MAX_BUFFER_BYTES)
                root = ET.fromstring(xml_content)

                paragraphs: list[str] = []
                for p in root.iter():
                    if p.tag.endswith("}p") or p.tag == "w:p":
                        runs = [
                            elem.text
                            for elem in p.iter()
                            if (elem.tag.endswith("}t") or elem.tag == "w:t")
                            and elem.text
                        ]
                        if runs:
                            paragraphs.append("".join(runs))

                if paragraphs:
                    raw_text = "\n".join(paragraphs)
                else:
                    runs = [
                        elem.text
                        for elem in root.iter()
                        if (elem.tag.endswith("}t") or elem.tag == "w:t")
                        and elem.text
                    ]
                    raw_text = " ".join(runs)

                return raw_text.strip() if raw_text else None
        except Exception as e:
            logger.debug("Failed to extract DOCX text from %s: %s", path, e)
            return None

    def _extract_pptx_text(self, path: str) -> str | None:
        """Extract slide text from .pptx with natural slide ordering."""
        try:
            with zipfile.ZipFile(path, "r") as zf:
                slide_entries: list[tuple[int, str]] = []
                for name in zf.namelist():
                    m = re.search(r"ppt/slides/slide(\d+)\.xml$", name)
                    if m:
                        slide_entries.append((int(m.group(1)), name))

                if not slide_entries:
                    return None

                slide_entries.sort(key=lambda x: x[0])
                all_slides: list[str] = []

                for _, slide_path in slide_entries:
                    with zf.open(slide_path) as f:
                        xml_content = f.read(MAX_BUFFER_BYTES)
                    root = ET.fromstring(xml_content)
                    slide_runs: list[str] = [
                        elem.text
                        for elem in root.iter()
                        if (elem.tag.endswith("}t") or elem.tag == "a:t")
                        and elem.text
                    ]
                    if slide_runs:
                        all_slides.append(" ".join(slide_runs))

                raw_text = "\n".join(all_slides).strip()
                return raw_text if raw_text else None
        except Exception as e:
            logger.debug("Failed to extract PPTX text from %s: %s", path, e)
            return None

    def _extract_odt_text(self, path: str) -> str | None:
        """Extract body text from .odt by reading content.xml."""
        try:
            with zipfile.ZipFile(path, "r") as zf:
                if "content.xml" not in zf.namelist():
                    return None
                with zf.open("content.xml") as f:
                    xml_content = f.read(MAX_BUFFER_BYTES)
                root = ET.fromstring(xml_content)
                text = " ".join(root.itertext()).strip()
                return text if text else None
        except Exception as e:
            logger.debug("Failed to extract ODT text from %s: %s", path, e)
            return None

    def _extract_tabular_text(self, path: str) -> str | None:
        """Parse tabular files (.csv, .tsv), sort data rows canonically, and generate canonical text."""
        try:
            with open(path, "rb") as bf:
                raw_bytes = bf.read(MAX_BUFFER_BYTES)

            if not raw_bytes or not raw_bytes.strip():
                return None

            if b"\x00" in raw_bytes:
                return None

            try:
                content_str = raw_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                content_str = raw_bytes.decode("latin-1", errors="replace")

            ext = Path(path).suffix.lower()
            delimiter = "\t" if ext == ".tsv" else ","

            # Sniff delimiter on sample
            sample = content_str[:8192]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                delimiter = dialect.delimiter
            except Exception:
                if ext == ".tsv":
                    delimiter = "\t"
                elif ext == ".csv":
                    delimiter = ","

            f_io = io.StringIO(content_str)
            reader = csv.reader(f_io, delimiter=delimiter)
            rows: list[list[str]] = []
            for row in reader:
                cleaned = [cell.strip() for cell in row]
                if any(cleaned):
                    rows.append(cleaned)

            if not rows:
                return None

            header = rows[0]
            data_rows = rows[1:]
            sorted_data = sorted(data_rows, key=tuple)

            header_line = "\t".join(header)
            data_lines = ["\t".join(r) for r in sorted_data]
            if data_lines:
                canonical_text = header_line + "\n" + "\n".join(data_lines)
            else:
                canonical_text = header_line

            return canonical_text
        except Exception as e:
            logger.debug("Failed to extract tabular data from %s: %s", path, e)
            return None

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict[str, Any] | None = None,
    ) -> list[DuplicateCluster]:
        """Find duplicate and near-duplicate document clusters."""
        supported = self.filter_supported(candidates)
        if len(supported) < 2:
            return []

        valid_entries: list[FileEntry] = []
        entry_data: list[tuple[str, str, int, set[str]]] = []

        for entry in supported:
            data = self._extract_document_data(entry.path)
            if data is not None:
                valid_entries.append(entry)
                entry_data.append(data)

        n = len(valid_entries)
        if n < 2:
            return []

        dsu = DisjointSetUnion(n)
        pairwise_sims: dict[tuple[int, int], float] = {}

        # Step 1: Exact normalized content matches (similarity 1.0)
        hash_groups: dict[str, list[int]] = defaultdict(list)
        for idx, (content_hash, _, _, _) in enumerate(entry_data):
            hash_groups[content_hash].append(idx)

        for _, group_indices in hash_groups.items():
            if len(group_indices) > 1:
                first = group_indices[0]
                for other in group_indices[1:]:
                    dsu.union(first, other)
                    pairwise_sims[(min(first, other), max(first, other))] = 1.0

        # Step 2: Token Jaccard similarity for near-duplicate candidates (similarity >= 0.90)
        for i in range(n):
            tokens_i = entry_data[i][3]
            len_i = len(tokens_i)
            if len_i < MIN_TOKENS_FOR_SIMILARITY:
                continue

            for j in range(i + 1, n):
                if dsu.find(i) == dsu.find(j):
                    continue

                tokens_j = entry_data[j][3]
                len_j = len(tokens_j)
                if len_j < MIN_TOKENS_FOR_SIMILARITY:
                    continue

                # Fast O(1) ratio pruning: min_len / max_len must be >= threshold
                min_len = min(len_i, len_j)
                max_len = max(len_i, len_j)
                if max_len == 0 or (min_len / max_len) < SIMILARITY_THRESHOLD:
                    continue

                inter = len(tokens_i & tokens_j)
                union = len(tokens_i | tokens_j)
                sim = inter / union if union > 0 else 0.0
                if sim >= SIMILARITY_THRESHOLD:
                    dsu.union(i, j)
                    pairwise_sims[(i, j)] = sim

        # Step 3: Form clusters
        cluster_counter = (context or {}).get("start_cluster_id", 1)
        cluster_map: dict[int, list[int]] = defaultdict(list)
        for idx in range(n):
            root = dsu.find(idx)
            cluster_map[root].append(idx)

        clusters: list[DuplicateCluster] = []
        for root, member_indices in cluster_map.items():
            if len(member_indices) < 2:
                continue

            members = [valid_entries[idx] for idx in member_indices]
            scores: list[float] = []
            for idx in member_indices:
                if idx == root:
                    scores.append(1.0)
                else:
                    pair_key = (min(root, idx), max(root, idx))
                    if pair_key in pairwise_sims:
                        scores.append(pairwise_sims[pair_key])
                    else:
                        alt_sims = [
                            pairwise_sims[(min(m, idx), max(m, idx))]
                            for m in member_indices
                            if m != idx and (min(m, idx), max(m, idx)) in pairwise_sims
                        ]
                        scores.append(max(alt_sims) if alt_sims else 1.0)

            exts = sorted(list({Path(m.path).suffix.lower() for m in members}))
            content_hashes = [entry_data[idx][0] for idx in member_indices]
            metadata: dict[str, Any] = {
                "extensions": exts,
                "content_hashes": content_hashes,
                "member_count": len(members),
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
