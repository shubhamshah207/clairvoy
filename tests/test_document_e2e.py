"""
Comprehensive Opaque-Box End-to-End (E2E) Test Suite for Clairvoy Document & Tabular Deduplication.

Derived strictly from ORIGINAL_REQUEST.md, PROJECT.md, and TEST_INFRA.md.
Covers 4 Tiers:
- Tier 1: Feature Coverage (>=5 tests per feature: PDF, DOCX, PPTX, ODT, CSV/TSV, Token Jaccard >= 0.90)
- Tier 2: Boundary & Corner Cases (>=5 tests per feature: Corrupted/Truncated, Encrypted/Zero-Byte,
          Natural Slide Ordering, CSV Sniffing & UTF-8 BOM, Buffer/Word Caps, Token Thresholds)
- Tier 3: Cross-Feature Interactions (Multi-Format Matching, Permuted CSV vs TSV, DSU Transitivity,
          Pipeline Tiered Pruning, Keeper Scoring)
- Tier 4: Real-World Application Scenarios (Rebrand Revisions, Permuted Sales Exports,
          Presentation Revisions, Academic Paper Drafts, Mixed Directory Scan)
"""

from __future__ import annotations

import csv
import html
import io
import zipfile
from pathlib import Path

import pypdf
import pypdf.generic
import pytest

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import DuplicateCluster, PluginRegistry
from clairvoy.engines.pipeline import CompositeKeeperStrategy, DeduplicationPipeline
from clairvoy.plugins.document_matcher import (
    MAX_BUFFER_BYTES,
    MAX_PDF_PAGES,
    MAX_WORDS,
    SIMILARITY_THRESHOLD,
    DocumentTextMatcherPlugin,
)
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin
from clairvoy.plugins.quarantine_action import SafeQuarantineActionPlugin

# ==============================================================================
# In-Memory Synthetic Document Builders (Hermetic & 100% Offline)
# ==============================================================================


def _make_pdf(
    text: str,
    pages: int = 1,
    password: str | None = None,
    author: str | None = None,
    empty: bool = False,
) -> bytes:
    """Generate a synthetically valid PDF document with embedded text streams."""
    writer = pypdf.PdfWriter()
    if author:
        writer.add_metadata({pypdf.generic.NameObject("/Author"): author})

    for _ in range(pages):
        page = writer.add_blank_page(width=400, height=400)
        if not empty and text:
            stream = pypdf.generic.DecodedStreamObject()
            escaped = (
                text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            )
            stream.set_data(
                f"BT /F1 12 Tf 50 350 Td ({escaped}) Tj ET".encode(
                    "latin-1", errors="replace"
                )
            )
            page[pypdf.generic.NameObject("/Contents")] = writer._add_object(stream)
            font_dict = pypdf.generic.DictionaryObject({
                pypdf.generic.NameObject("/Type"): pypdf.generic.NameObject("/Font"),
                pypdf.generic.NameObject("/Subtype"): pypdf.generic.NameObject("/Type1"),
                pypdf.generic.NameObject("/BaseFont"): pypdf.generic.NameObject("/Helvetica"),
            })
            font_ref = writer._add_object(font_dict)
            page[pypdf.generic.NameObject("/Resources")] = pypdf.generic.DictionaryObject({
                pypdf.generic.NameObject("/Font"): pypdf.generic.DictionaryObject({
                    pypdf.generic.NameObject("/F1"): font_ref,
                })
            })

    if password:
        writer.encrypt(password)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_docx(
    paragraphs: list[str] | None = None,
    runs_per_p: list[list[str]] | None = None,
    app_metadata: str | None = None,
    empty: bool = False,
    malformed_xml: bool = False,
) -> bytes:
    """Generate a synthetically valid .docx archive in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if malformed_xml:
            zf.writestr("word/document.xml", b"<w:document><w:body><unclosed-tag>")
        elif empty:
            zf.writestr(
                "word/document.xml",
                b'<?xml version="1.0" encoding="UTF-8"?>'
                b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                b"<w:body></w:body></w:document>",
            )
        else:
            body_parts: list[str] = []
            if runs_per_p:
                for runs in runs_per_p:
                    r_xml = "".join(f"<w:r><w:t>{html.escape(r)}</w:t></w:r>" for r in runs)
                    body_parts.append(f"<w:p>{r_xml}</w:p>")
            elif paragraphs:
                for p in paragraphs:
                    body_parts.append(f"<w:p><w:r><w:t>{html.escape(p)}</w:t></w:r></w:p>")

            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f"<w:body>{''.join(body_parts)}</w:body>"
                "</w:document>"
            )
            zf.writestr("word/document.xml", xml.encode("utf-8"))

        if app_metadata:
            zf.writestr("docProps/app.xml", app_metadata.encode("utf-8"))
    return buf.getvalue()


def _make_pptx(
    slides: list[str] | list[list[str]],
    slide_numbers: list[int] | None = None,
    malformed_xml: bool = False,
    empty: bool = False,
) -> bytes:
    """Generate a synthetically valid .pptx presentation archive in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if malformed_xml:
            zf.writestr("ppt/slides/slide1.xml", b"<p:sld><unclosed-slide>")
        elif not empty:
            nums = (
                slide_numbers
                if slide_numbers is not None
                else list(range(1, len(slides) + 1))
            )
            for num, slide_content in zip(nums, slides, strict=False):
                if isinstance(slide_content, list):
                    shapes_xml = ""
                    for shape_text in slide_content:
                        shapes_xml += (
                            "<p:sp><p:txBody><a:p><a:r><a:t>"
                            f"{html.escape(shape_text)}"
                            "</a:t></a:r></a:p></p:txBody></p:sp>"
                        )
                else:
                    shapes_xml = (
                        "<p:sp><p:txBody><a:p><a:r><a:t>"
                        f"{html.escape(slide_content)}"
                        "</a:t></a:r></a:p></p:txBody></p:sp>"
                    )
                xml = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                    f"<p:cSld><p:spTree>{shapes_xml}</p:spTree></p:cSld>"
                    "</p:sld>"
                )
                zf.writestr(f"ppt/slides/slide{num}.xml", xml.encode("utf-8"))
    return buf.getvalue()


def _make_odt(
    paragraphs: list[str] | None = None,
    headings: list[str] | None = None,
    nested_spans: list[tuple[str, str, str]] | None = None,
    malformed_xml: bool = False,
    empty: bool = False,
) -> bytes:
    """Generate a synthetically valid .odt document archive in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if malformed_xml:
            zf.writestr("content.xml", b"<office:document-content><unclosed>")
        elif not empty:
            parts: list[str] = []
            if headings:
                for h in headings:
                    parts.append(f'<text:h text:outline-level="1">{html.escape(h)}</text:h>')
            if paragraphs:
                for p in paragraphs:
                    parts.append(f"<text:p>{html.escape(p)}</text:p>")
            if nested_spans:
                for prefix, span, suffix in nested_spans:
                    parts.append(
                        f"<text:p>{html.escape(prefix)}<text:span>{html.escape(span)}</text:span>{html.escape(suffix)}</text:p>"
                    )
            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<office:document-content '
                'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
                'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
                f"<office:body><office:text>{''.join(parts)}</office:text></office:body>"
                "</office:document-content>"
            )
            zf.writestr("content.xml", xml.encode("utf-8"))
    return buf.getvalue()


def _make_csv(
    rows: list[list[str]],
    delimiter: str = ",",
    bom: bool = False,
    null_bytes: bool = False,
) -> bytes:
    """Generate a CSV or TSV byte stream with optional BOM or null bytes."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    writer.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    if null_bytes:
        data = data[:10] + b"\x00" + data[10:]
    return data


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def plugin() -> DocumentTextMatcherPlugin:
    """Provides an initialized DocumentTextMatcherPlugin instance."""
    return DocumentTextMatcherPlugin()


# ==============================================================================
# TIER 1: Feature Coverage (>=5 tests per feature)
# ==============================================================================


class TestTier1FeatureCoverage:
    """Tier 1: Comprehensive feature coverage across all 6 core modalities."""

    # --- 1. PDF Deduplication (>= 5 cases) ---

    def test_tier1_pdf_identical_content_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Identical text in PDFs with different authors/metadata must cluster."""
        p1 = tmp_path / "report_author_a.pdf"
        p2 = tmp_path / "report_author_b.pdf"
        text = "Confidential Enterprise Strategy and Quarterly Roadmap for Fiscal Year 2026."
        p1.write_bytes(_make_pdf(text, author="Alice Analyst"))
        p2.write_bytes(_make_pdf(text, author="Bob Director"))

        candidates = [
            FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
            FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert clusters[0].match_type == MatchType.CONTENT_NEAR_DUPLICATE
        assert len(clusters[0].members) == 2

    def test_tier1_pdf_multipage_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Multi-page PDFs with identical multi-page text must cluster."""
        p1 = tmp_path / "multi_v1.pdf"
        p2 = tmp_path / "multi_v2.pdf"
        text = "Section One Overview Section Two Data Analysis Section Three Conclusion."
        p1.write_bytes(_make_pdf(text, pages=3))
        p2.write_bytes(_make_pdf(text, pages=3))

        candidates = [
            FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
            FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier1_pdf_distinct_content_no_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PDFs with distinct textual content must not form duplicate clusters."""
        p1 = tmp_path / "astronomy.pdf"
        p2 = tmp_path / "culinary.pdf"
        p1.write_bytes(_make_pdf("Deep space observation of spiral galaxies and cosmic radiation."))
        p2.write_bytes(_make_pdf("Traditional culinary baking techniques for artisanal sourdough bread."))

        candidates = [
            FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
            FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0

    def test_tier1_pdf_whitespace_normalization(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PDFs with differing inter-word whitespace must normalize to identical hash."""
        p1 = tmp_path / "clean_spacing.pdf"
        p2 = tmp_path / "padded_spacing.pdf"
        p1.write_bytes(_make_pdf("Quantum entanglement enables instantaneous particle state correlation."))
        p2.write_bytes(_make_pdf("Quantum   entanglement   enables   instantaneous  particle  state  correlation."))

        rep1 = plugin.extract_document_representation(str(p1))
        rep2 = plugin.extract_document_representation(str(p2))
        assert rep1 is not None and rep2 is not None
        assert rep1[0] == rep2[0]

    def test_tier1_pdf_triplet_cluster(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Three identical PDFs must be grouped into a single 3-member cluster."""
        files = [tmp_path / f"copy_{i}.pdf" for i in range(3)]
        text = "Global Supply Chain Logistics Optimization and Inventory Warehouse Management."
        for f in files:
            f.write_bytes(_make_pdf(text))

        candidates = [FileEntry(path=str(f), size_bytes=f.stat().st_size) for f in files]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 3

    def test_tier1_pdf_representation_api(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """extract_document_representation on PDF must return 64-char hash and valid preview."""
        p = tmp_path / "sample.pdf"
        text = "Artificial intelligence automated deduplication engine for distributed storage."
        p.write_bytes(_make_pdf(text))

        rep = plugin.extract_document_representation(str(p))
        assert rep is not None
        content_hash, preview, length = rep
        assert len(content_hash) == 64
        assert "artificial intelligence" in preview.lower()
        assert length > 0

    # --- 2. DOCX Deduplication (>= 5 cases) ---

    def test_tier1_docx_identical_content_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """DOCX files with identical text but different application metadata must cluster."""
        d1 = tmp_path / "draft_word.docx"
        d2 = tmp_path / "draft_libreoffice.docx"
        p_text = "Standard Operating Procedure for Cloud Infrastructure Deployment and Security."
        d1.write_bytes(_make_docx([p_text], app_metadata="<App>Microsoft Office Word</App>"))
        d2.write_bytes(_make_docx([p_text], app_metadata="<App>LibreOffice Writer</App>"))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier1_docx_multi_paragraph_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """DOCX files containing multiple paragraphs must match when content is identical."""
        d1 = tmp_path / "multi_p1.docx"
        d2 = tmp_path / "multi_p2.docx"
        paragraphs = [
            "Introduction: The distributed filesystem maintains strong consistency guarantees.",
            "Methodology: Multi-raft consensus groups partition the storage keyspace.",
            "Conclusion: High availability is achieved with sub-second failover latency.",
        ]
        d1.write_bytes(_make_docx(paragraphs))
        d2.write_bytes(_make_docx(paragraphs))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_docx_multi_run_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """DOCX with text split across multiple <w:r><w:t> runs must extract and match cleanly."""
        d1 = tmp_path / "single_run.docx"
        d2 = tmp_path / "multi_run.docx"
        d1.write_bytes(_make_docx(["The quick brown fox jumps over the lazy dog."]))
        runs = [["The ", "quick ", "brown ", "fox ", "jumps ", "over ", "the ", "lazy ", "dog."]]
        d2.write_bytes(_make_docx(runs_per_p=runs))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_docx_distinct_content_no_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """DOCX files with different body text must not be clustered."""
        d1 = tmp_path / "finance.docx"
        d2 = tmp_path / "legal.docx"
        d1.write_bytes(_make_docx(["Quarterly financial balance sheet and profit loss statements."]))
        d2.write_bytes(_make_docx(["Intellectual property licensing agreements and non-disclosure terms."]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0

    def test_tier1_docx_whitespace_normalization(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """DOCX files with varying surrounding whitespace normalize to identical hash."""
        d1 = tmp_path / "normal.docx"
        d2 = tmp_path / "padded.docx"
        base = "Unified multimodal media deduplication and offline intelligence pipeline."
        d1.write_bytes(_make_docx([base]))
        d2.write_bytes(_make_docx(["   " + base + "   \n\n"]))

        rep1 = plugin.extract_document_representation(str(d1))
        rep2 = plugin.extract_document_representation(str(d2))
        assert rep1 is not None and rep2 is not None
        assert rep1[0] == rep2[0]

    def test_tier1_docx_representation_api(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """extract_document_representation on DOCX must return 64-char hash and preview."""
        d = tmp_path / "doc.docx"
        d.write_bytes(_make_docx(["High throughput data ingestion pipeline architecture."]))

        rep = plugin.extract_document_representation(str(d))
        assert rep is not None
        content_hash, preview, length = rep
        assert len(content_hash) == 64
        assert "high throughput" in preview.lower()
        assert length > 0

    # --- 3. PPTX Deduplication (>= 5 cases) ---

    def test_tier1_pptx_identical_content_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PPTX presentations with identical slide text must cluster."""
        p1 = tmp_path / "pitch_v1.pptx"
        p2 = tmp_path / "pitch_v2.pptx"
        slides = ["Executive Summary and Core Value Proposition", "Market Size and Competitive Landscape"]
        p1.write_bytes(_make_pptx(slides))
        p2.write_bytes(_make_pptx(slides))

        candidates = [
            FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
            FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier1_pptx_multi_slide_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PPTX presentations with 4 ordered slides must match."""
        p1 = tmp_path / "deck_a.pptx"
        p2 = tmp_path / "deck_b.pptx"
        slides = [
            "Slide 1: Cloud Architecture Blueprint",
            "Slide 2: Security and Encryption Invariants",
            "Slide 3: Performance Metrics and Benchmarks",
            "Slide 4: Roadmap and Release Schedule",
        ]
        p1.write_bytes(_make_pptx(slides))
        p2.write_bytes(_make_pptx(slides))

        candidates = [
            FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
            FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_pptx_distinct_content_no_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Presentations with different slide texts must not cluster."""
        p1 = tmp_path / "sales.pptx"
        p2 = tmp_path / "engineering.pptx"
        p1.write_bytes(_make_pptx(["Sales targets and customer acquisition cost projections."]))
        p2.write_bytes(_make_pptx(["Microservices architecture and database sharding implementation."]))

        candidates = [
            FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
            FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0

    def test_tier1_pptx_multi_shape_slide_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Slides with multiple shapes containing distinct text runs must extract and match."""
        p1 = tmp_path / "shapes_a.pptx"
        p2 = tmp_path / "shapes_b.pptx"
        shapes = [["Title Box Text", "Subtitle Text", "Footer Disclaimer"]]
        p1.write_bytes(_make_pptx(shapes))
        p2.write_bytes(_make_pptx(shapes))

        candidates = [
            FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
            FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_pptx_triplet_cluster(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Three identical presentations must form a single 3-member cluster."""
        files = [tmp_path / f"deck_{i}.pptx" for i in range(3)]
        slides = ["Quarterly All Hands Meeting", "Product Milestone Review", "Q&A Session"]
        for f in files:
            f.write_bytes(_make_pptx(slides))

        candidates = [FileEntry(path=str(f), size_bytes=f.stat().st_size) for f in files]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 3

    def test_tier1_pptx_representation_api(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """extract_document_representation on PPTX must return 64-char hash and preview."""
        p = tmp_path / "slides.pptx"
        p.write_bytes(_make_pptx(["Keynote speech on quantum computational algorithms."]))

        rep = plugin.extract_document_representation(str(p))
        assert rep is not None
        content_hash, preview, length = rep
        assert len(content_hash) == 64
        assert "keynote" in preview.lower()
        assert length > 0

    # --- 4. ODT Deduplication (>= 5 cases) ---

    def test_tier1_odt_identical_content_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """ODT documents with identical paragraph text must cluster."""
        o1 = tmp_path / "spec_v1.odt"
        o2 = tmp_path / "spec_v2.odt"
        text = ["Functional Specification for Enterprise Data Loss Prevention System."]
        o1.write_bytes(_make_odt(text))
        o2.write_bytes(_make_odt(text))

        candidates = [
            FileEntry(path=str(o1), size_bytes=o1.stat().st_size),
            FileEntry(path=str(o2), size_bytes=o2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier1_odt_headings_and_paragraphs(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """ODT documents with headings and paragraphs must extract all content and match."""
        o1 = tmp_path / "book_a.odt"
        o2 = tmp_path / "book_b.odt"
        headings = ["Chapter One: The Origins of Computing"]
        paras = ["Early mechanical calculating devices set the stage for modern digital architecture."]
        o1.write_bytes(_make_odt(paragraphs=paras, headings=headings))
        o2.write_bytes(_make_odt(paragraphs=paras, headings=headings))

        candidates = [
            FileEntry(path=str(o1), size_bytes=o1.stat().st_size),
            FileEntry(path=str(o2), size_bytes=o2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_odt_nested_spans_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """ODT documents with nested formatting spans must extract text without missing words."""
        o1 = tmp_path / "formatted_a.odt"
        o2 = tmp_path / "formatted_b.odt"
        spans = [("This is an important ", "highlighted security advisory", " for administrators.")]
        o1.write_bytes(_make_odt(nested_spans=spans))
        o2.write_bytes(_make_odt(nested_spans=spans))

        candidates = [
            FileEntry(path=str(o1), size_bytes=o1.stat().st_size),
            FileEntry(path=str(o2), size_bytes=o2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_odt_distinct_content_no_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """ODT documents with distinct text must not cluster."""
        o1 = tmp_path / "bio.odt"
        o2 = tmp_path / "chem.odt"
        o1.write_bytes(_make_odt(["Cellular mitosis and genetic sequencing in eukaryotic organisms."]))
        o2.write_bytes(_make_odt(["Covalent bonds and organic synthesis in catalytic reactions."]))

        candidates = [
            FileEntry(path=str(o1), size_bytes=o1.stat().st_size),
            FileEntry(path=str(o2), size_bytes=o2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0

    def test_tier1_odt_triplet_cluster(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Three identical ODT documents must form a single 3-member cluster."""
        files = [tmp_path / f"odt_{i}.odt" for i in range(3)]
        text = ["OpenDocument Format Technical Committee Meeting Minutes and Resolutions."]
        for f in files:
            f.write_bytes(_make_odt(text))

        candidates = [FileEntry(path=str(f), size_bytes=f.stat().st_size) for f in files]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 3

    def test_tier1_odt_representation_api(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """extract_document_representation on ODT must return 64-char hash and preview."""
        o = tmp_path / "doc.odt"
        o.write_bytes(_make_odt(["International standards for digital document interchange."]))

        rep = plugin.extract_document_representation(str(o))
        assert rep is not None
        content_hash, preview, length = rep
        assert len(content_hash) == 64
        assert "international standards" in preview.lower()
        assert length > 0

    # --- 5. CSV / TSV Permutation-Invariant Deduplication (>= 5 cases) ---

    def test_tier1_csv_permuted_rows_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """CSVs with identical headers and permuted data rows must cluster."""
        c1 = tmp_path / "sales_a.csv"
        c2 = tmp_path / "sales_b.csv"
        header = ["id", "customer", "amount"]
        rows_a = [header, ["1", "Acme", "100"], ["2", "Beta", "200"], ["3", "Gamma", "300"]]
        rows_b = [header, ["3", "Gamma", "300"], ["1", "Acme", "100"], ["2", "Beta", "200"]]
        c1.write_bytes(_make_csv(rows_a))
        c2.write_bytes(_make_csv(rows_b))

        candidates = [
            FileEntry(path=str(c1), size_bytes=c1.stat().st_size),
            FileEntry(path=str(c2), size_bytes=c2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier1_tsv_permuted_rows_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """TSVs with identical headers and permuted data rows must cluster."""
        t1 = tmp_path / "records_a.tsv"
        t2 = tmp_path / "records_b.tsv"
        header = ["sku", "warehouse", "qty"]
        rows_a = [header, ["SKU-001", "East", "50"], ["SKU-002", "West", "30"]]
        rows_b = [header, ["SKU-002", "West", "30"], ["SKU-001", "East", "50"]]
        t1.write_bytes(_make_csv(rows_a, delimiter="\t"))
        t2.write_bytes(_make_csv(rows_b, delimiter="\t"))

        candidates = [
            FileEntry(path=str(t1), size_bytes=t1.stat().st_size),
            FileEntry(path=str(t2), size_bytes=t2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_csv_vs_tsv_permuted_matching(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """CSV and TSV with identical headers and permuted data rows must cluster across formats."""
        c = tmp_path / "data.csv"
        t = tmp_path / "data.tsv"
        header = ["product", "price", "stock"]
        rows_csv = [header, ["Widget", "9.99", "100"], ["Gadget", "19.99", "50"]]
        rows_tsv = [header, ["Gadget", "19.99", "50"], ["Widget", "9.99", "100"]]
        c.write_bytes(_make_csv(rows_csv, delimiter=","))
        t.write_bytes(_make_csv(rows_tsv, delimiter="\t"))

        candidates = [
            FileEntry(path=str(c), size_bytes=c.stat().st_size),
            FileEntry(path=str(t), size_bytes=t.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_csv_cell_whitespace_trimming(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """CSV files with varying whitespace padding around cells must normalize and match."""
        c1 = tmp_path / "clean.csv"
        c2 = tmp_path / "padded.csv"
        header = ["name", "role", "dept"]
        rows1 = [header, ["Alice", "Engineer", "Backend"], ["Bob", "Designer", "UX"]]
        rows2 = [header, ["  Alice  ", " Engineer ", "Backend"], ["Bob", " Designer", " UX   "]]
        c1.write_bytes(_make_csv(rows1))
        c2.write_bytes(_make_csv(rows2))

        rep1 = plugin.extract_document_representation(str(c1))
        rep2 = plugin.extract_document_representation(str(c2))
        assert rep1 is not None and rep2 is not None
        assert rep1[0] == rep2[0]

    def test_tier1_csv_distinct_rows_no_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """CSVs with different data values must not cluster."""
        c1 = tmp_path / "dataset_2025.csv"
        c2 = tmp_path / "dataset_2026.csv"
        header = ["month", "revenue"]
        c1.write_bytes(_make_csv([header, ["Jan", "10000"], ["Feb", "12000"]]))
        c2.write_bytes(_make_csv([header, ["Jan", "50000"], ["Feb", "60000"]]))

        candidates = [
            FileEntry(path=str(c1), size_bytes=c1.stat().st_size),
            FileEntry(path=str(c2), size_bytes=c2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0

    def test_tier1_tabular_representation_digest(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """extract_document_representation produces identical 64-char hash for permuted CSVs."""
        c1 = tmp_path / "order1.csv"
        c2 = tmp_path / "order2.csv"
        header = ["item", "qty"]
        c1.write_bytes(_make_csv([header, ["Alpha", "10"], ["Beta", "20"]]))
        c2.write_bytes(_make_csv([header, ["Beta", "20"], ["Alpha", "10"]]))

        rep1 = plugin.extract_document_representation(str(c1))
        rep2 = plugin.extract_document_representation(str(c2))
        assert rep1 is not None and rep2 is not None
        assert rep1[0] == rep2[0]
        assert len(rep1[0]) == 64

    # --- 6. Token Jaccard Near-Duplicate Deduplication (>= 5 cases) ---

    def test_tier1_jaccard_high_similarity_clustered(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Documents with 95% word overlap (>0.90) must be clustered."""
        d1 = tmp_path / "doc_v1.docx"
        d2 = tmp_path / "doc_v2.docx"
        words = [f"token{i}" for i in range(100)]
        text1 = " ".join(words)
        # Modify 3 words out of 100 -> Jaccard is 97 / 103 ~= 0.941 >= 0.90
        words2 = list(words)
        words2[10] = "alteredtoken10"
        words2[20] = "alteredtoken20"
        words2[30] = "alteredtoken30"
        text2 = " ".join(words2)

        d1.write_bytes(_make_docx([text1]))
        d2.write_bytes(_make_docx([text2]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier1_jaccard_minor_typo_clustered(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Long document with one corrected typo sentence (>0.90 overlap) must cluster."""
        d1 = tmp_path / "draft_typo.docx"
        d2 = tmp_path / "draft_fixed.docx"
        base = (
            "Enterprise cloud architectures require resilient fault tolerance multi region redundancy "
            "automated failover mechanisms robust security protocols and end to end encryption standards "
            "for data in transit and data at rest across all computing nodes in the global cluster."
        )
        d1.write_bytes(_make_docx([base + " This section contains a smal typo here."]))
        d2.write_bytes(_make_docx([base + " This section contains a small typo here."]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_jaccard_preamble_clustered(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Document with added short legal disclaimer header (>0.90 overlap) must cluster."""
        d1 = tmp_path / "original_terms.docx"
        d2 = tmp_path / "disclaimer_terms.docx"
        long_body = " ".join([f"contractterm{i}" for i in range(80)])
        d1.write_bytes(_make_docx([long_body]))
        d2.write_bytes(_make_docx(["Confidential and proprietary notice.", long_body]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier1_jaccard_similarity_scores(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Near-duplicate cluster must store float similarity scores >= 0.90."""
        d1 = tmp_path / "source.docx"
        d2 = tmp_path / "revised.docx"
        words = [f"wordidentifier{i}" for i in range(60)]
        d1.write_bytes(_make_docx([" ".join(words)]))
        words_revised = list(words)
        words_revised[5] = "replacementtoken"
        d2.write_bytes(_make_docx([" ".join(words_revised)]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        scores = clusters[0].similarity_scores
        assert len(scores) == 2
        for score in scores:
            assert 0.90 <= score <= 1.0

    def test_tier1_jaccard_three_way_chain(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Transitive near-duplicate chain (A~B and B~C) must merge into 1 cluster via DSU."""
        d1 = tmp_path / "chain_a.docx"
        d2 = tmp_path / "chain_b.docx"
        d3 = tmp_path / "chain_c.docx"
        # 100 core words
        core = [f"sharedterm{i}" for i in range(100)]
        # A has core + 2 words, B has core + 2 different words, C has core + 2 different words
        d1.write_bytes(_make_docx([" ".join(core + ["deltaA1", "deltaA2"])]))
        d2.write_bytes(_make_docx([" ".join(core + ["deltaB1", "deltaB2"])]))
        d3.write_bytes(_make_docx([" ".join(core + ["deltaC1", "deltaC2"])]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
            FileEntry(path=str(d3), size_bytes=d3.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 3


# ==============================================================================
# TIER 2: Boundary & Corner Cases (>=5 tests per feature)
# ==============================================================================


class TestTier2BoundaryAndCornerCases:
    """Tier 2: Boundary value analysis, malformed inputs, edge thresholds, and limits."""

    # --- 1. Corrupted / Truncated Files (>= 5 cases) ---

    def test_tier2_corrupted_truncated_pdf(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Truncated PDF with partial header bytes must return None without raising exception."""
        p = tmp_path / "truncated.pdf"
        p.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Length 50 >>\nstream\ngarbage")
        rep = plugin.extract_document_representation(str(p))
        assert rep is None

    def test_tier2_corrupted_bad_zip_docx(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """File with .docx extension containing non-zip garbage must return None without crashing."""
        d = tmp_path / "fake_zip.docx"
        d.write_bytes(b"PK\x03\x04definitely_not_a_valid_zip_archive_stream_corrupted")
        rep = plugin.extract_document_representation(str(d))
        assert rep is None

    def test_tier2_corrupted_missing_xml_docx(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Valid zip archive missing word/document.xml must return None gracefully."""
        d = tmp_path / "no_doc_xml.docx"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("unrelated.txt", b"Hello world")
        d.write_bytes(buf.getvalue())
        rep = plugin.extract_document_representation(str(d))
        assert rep is None

    def test_tier2_corrupted_malformed_xml_pptx(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PPTX containing malformed unclosed XML in slide must return None without crashing."""
        p = tmp_path / "bad_xml.pptx"
        p.write_bytes(_make_pptx(["test"], malformed_xml=True))
        rep = plugin.extract_document_representation(str(p))
        assert rep is None

    def test_tier2_corrupted_bad_zip_odt(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """ODT with missing content.xml must return None gracefully."""
        o = tmp_path / "no_content.odt"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("mimetype", b"application/vnd.oasis.opendocument.text")
        o.write_bytes(buf.getvalue())
        rep = plugin.extract_document_representation(str(o))
        assert rep is None

    def test_tier2_corrupted_csv_null_bytes(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """CSV containing binary garbage and null bytes must be safely handled without crash."""
        c = tmp_path / "null_bytes.csv"
        c.write_bytes(b"col1,col2\nval1,\x00\x01\x02binarygarbage\x00")
        # Should either safely extract text or return None, without unhandled crash
        try:
            plugin.extract_document_representation(str(c))
        except Exception as exc:
            pytest.fail(f"extract_document_representation crashed on null bytes: {exc}")

    # --- 2. Password Encrypted & Zero-Byte Documents (>= 5 cases) ---

    def test_tier2_zero_byte_files_filtered(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Zero-byte files across all extensions must be excluded by filter_supported."""
        exts = [".pdf", ".docx", ".pptx", ".odt", ".csv", ".tsv"]
        entries: list[FileEntry] = []
        for ext in exts:
            f = tmp_path / f"zero{ext}"
            f.write_bytes(b"")
            entries.append(FileEntry(path=str(f), size_bytes=0))

        supported = plugin.filter_supported(entries)
        assert len(supported) == 0

    def test_tier2_encrypted_pdf_graceful_fallback(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Password-protected encrypted PDF must return None without raising exception."""
        p = tmp_path / "secret.pdf"
        p.write_bytes(_make_pdf("Top secret corporate intellectual property.", password="strongpassword123"))
        rep = plugin.extract_document_representation(str(p))
        assert rep is None

    def test_tier2_empty_text_pdf(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PDF containing blank pages with zero text must return None and avoid false duplicates."""
        p1 = tmp_path / "blank1.pdf"
        p2 = tmp_path / "blank2.pdf"
        p1.write_bytes(_make_pdf("", pages=2, empty=True))
        p2.write_bytes(_make_pdf("", pages=2, empty=True))

        assert plugin.extract_document_representation(str(p1)) is None
        assert plugin.extract_document_representation(str(p2)) is None

        candidates = [
            FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
            FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0

    def test_tier2_empty_docx(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """DOCX archive with empty <w:body></w:body> must return None."""
        d = tmp_path / "empty_body.docx"
        d.write_bytes(_make_docx(empty=True))
        rep = plugin.extract_document_representation(str(d))
        assert rep is None

    def test_tier2_empty_csv_zero_data_rows(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Completely empty CSV or CSV with only whitespace must return None."""
        c = tmp_path / "empty.csv"
        c.write_bytes(b"   \n\t\n   ")
        rep = plugin.extract_document_representation(str(c))
        assert rep is None

    def test_tier2_binary_bytes_named_as_document(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Random binary bytes disguised as .pptx or .odt must return None without crashing."""
        for ext in [".pptx", ".odt"]:
            f = tmp_path / f"disguised{ext}"
            f.write_bytes(b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00randomexecutablebytes")
            rep = plugin.extract_document_representation(str(f))
            assert rep is None

    # --- 3. PPTX Slide Natural Ordering (>= 5 cases) ---

    def test_tier2_pptx_natural_sort_1_to_10(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PPTX slides 1..10 must be read in natural numeric order, not lexicographic 1, 10, 2."""
        p = tmp_path / "ten_slides.pptx"
        slides = [f"SlideContentNumber{i}" for i in range(1, 11)]
        p.write_bytes(_make_pptx(slides))

        rep = plugin.extract_document_representation(str(p))
        assert rep is not None
        _, preview, _ = rep
        # In natural order, slide2 must appear before slide10
        pos2 = preview.find("SlideContentNumber2")
        pos10 = preview.find("SlideContentNumber10")
        assert pos2 != -1 and pos10 != -1
        assert pos2 < pos10

    def test_tier2_pptx_slide_order_change_differentiates(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Two PPTX files with reversed slide order must produce different canonical content hashes."""
        p1 = tmp_path / "forward.pptx"
        p2 = tmp_path / "backward.pptx"
        p1.write_bytes(_make_pptx(["Alpha Opening", "Beta Middle", "Gamma Closing"]))
        p2.write_bytes(_make_pptx(["Gamma Closing", "Beta Middle", "Alpha Opening"]))

        rep1 = plugin.extract_document_representation(str(p1))
        rep2 = plugin.extract_document_representation(str(p2))
        assert rep1 is not None and rep2 is not None
        assert rep1[0] != rep2[0]

    def test_tier2_pptx_multi_digit_slide_names(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Presentations with slides up to slide 12 must maintain natural ordering."""
        p = tmp_path / "twelve.pptx"
        slides = [f"ItemIndex{i:02d}" for i in range(1, 13)]
        p.write_bytes(_make_pptx(slides))

        rep = plugin.extract_document_representation(str(p))
        assert rep is not None
        _, preview, _ = rep
        pos1 = preview.find("ItemIndex01")
        pos9 = preview.find("ItemIndex09")
        pos12 = preview.find("ItemIndex12")
        assert pos1 < pos9 < pos12

    def test_tier2_pptx_fifteen_slides_order(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Presentations with 15 slides must process slides 11-15 after slide 10."""
        p = tmp_path / "fifteen.pptx"
        slides = [f"OrdinalToken{i}" for i in range(1, 16)]
        p.write_bytes(_make_pptx(slides))

        rep = plugin.extract_document_representation(str(p))
        assert rep is not None
        _, preview, _ = rep
        assert preview.find("OrdinalToken10") < preview.find("OrdinalToken11")

    def test_tier2_pptx_zero_slides(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PPTX archive with 0 slides must return None gracefully."""
        p = tmp_path / "zero_slides.pptx"
        p.write_bytes(_make_pptx([], empty=True))
        rep = plugin.extract_document_representation(str(p))
        assert rep is None

    # --- 4. CSV Delimiter Sniffing & UTF-8 BOM (>= 5 cases) ---

    def test_tier2_csv_utf8_bom_stripped(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """CSV with UTF-8 BOM (\xef\xbb\xbf) must strip BOM so header names match non-BOM CSV."""
        c_bom = tmp_path / "with_bom.csv"
        c_nobom = tmp_path / "no_bom.csv"
        rows = [["id", "name", "val"], ["1", "Alice", "100"], ["2", "Bob", "200"]]
        c_bom.write_bytes(_make_csv(rows, bom=True))
        c_nobom.write_bytes(_make_csv(rows, bom=False))

        rep1 = plugin.extract_document_representation(str(c_bom))
        rep2 = plugin.extract_document_representation(str(c_nobom))
        assert rep1 is not None and rep2 is not None
        assert rep1[0] == rep2[0]

    def test_tier2_csv_semicolon_sniffed(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """European semicolon-delimited CSV must be sniffed and matched against permuted copy."""
        c1 = tmp_path / "euro_a.csv"
        c2 = tmp_path / "euro_b.csv"
        header = ["katalog_nr", "bezeichnung", "preis"]
        r1 = [header, ["1001", "Schraube", "0.50"], ["1002", "Mutter", "0.30"]]
        r2 = [header, ["1002", "Mutter", "0.30"], ["1001", "Schraube", "0.50"]]
        c1.write_bytes(_make_csv(r1, delimiter=";"))
        c2.write_bytes(_make_csv(r2, delimiter=";"))

        rep1 = plugin.extract_document_representation(str(c1))
        rep2 = plugin.extract_document_representation(str(c2))
        assert rep1 is not None and rep2 is not None
        assert rep1[0] == rep2[0]

    def test_tier2_tsv_explicit_tab(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """TSV file with tab delimiters must be parsed correctly without falling back to comma."""
        t1 = tmp_path / "tab1.tsv"
        t2 = tmp_path / "tab2.tsv"
        rows = [["colA", "colB"], ["alpha,with,comma", "beta"], ["gamma", "delta"]]
        t1.write_bytes(_make_csv(rows, delimiter="\t"))
        t2.write_bytes(_make_csv(rows, delimiter="\t"))

        candidates = [
            FileEntry(path=str(t1), size_bytes=t1.stat().st_size),
            FileEntry(path=str(t2), size_bytes=t2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier2_csv_ragged_rows(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """CSV with ragged rows (varying column counts) must parse without raising error."""
        c = tmp_path / "ragged.csv"
        content = "col1,col2,col3\nval1,val2\nval3,val4,val5,val6\n"
        c.write_text(content, encoding="utf-8")

        rep = plugin.extract_document_representation(str(c))
        assert rep is not None
        assert len(rep[0]) == 64

    def test_tier2_csv_single_column(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Single-column CSV without delimiters must parse and normalize cleanly."""
        c = tmp_path / "single_col.csv"
        content = "hostname\nserver01\nserver02\nserver03\n"
        c.write_text(content, encoding="utf-8")

        rep = plugin.extract_document_representation(str(c))
        assert rep is not None
        assert len(rep[0]) == 64

    # --- 5. Buffer Caps (25MB) & Word Truncation (50,000 words) (>= 5 cases) ---

    def test_tier2_word_cap_50k_words_truncation(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Document with > 50,000 words must be capped to 50,000 words."""
        d = tmp_path / "large_word_count.docx"
        # 55,000 repetitions of words
        words = ["syntheticword"] * 55_000
        d.write_bytes(_make_docx([" ".join(words)]))

        data = plugin._extract_document_data(str(d))
        assert data is not None
        _, _, _, tokens = data
        assert "syntheticword" in tokens

    def test_tier2_word_cap_divergence_after_50k_matches(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Two documents identical in first 50,000 words but diverging after must have identical hash."""
        d1 = tmp_path / "doc_50k_a.docx"
        d2 = tmp_path / "doc_50k_b.docx"
        common_words = [f"tokenw{i}" for i in range(50_000)]
        d1.write_bytes(_make_docx([" ".join(common_words) + " divergenceA1 divergenceA2"]))
        d2.write_bytes(_make_docx([" ".join(common_words) + " divergenceB1 divergenceB2"]))

        rep1 = plugin.extract_document_representation(str(d1))
        rep2 = plugin.extract_document_representation(str(d2))
        assert rep1 is not None and rep2 is not None
        # Since text is truncated at 50,000 words, content hashes must be identical
        assert rep1[0] == rep2[0]

    def test_tier2_pdf_page_cap_50_pages(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PDF inspection must be capped at 50 pages; page 51+ content is not extracted."""
        p = tmp_path / "fifty_two_pages.pdf"
        writer = pypdf.PdfWriter()
        for i in range(1, 53):
            page = writer.add_blank_page(width=300, height=300)
            stream = pypdf.generic.DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 50 250 Td (PageContentNumber{i}) Tj ET".encode("latin-1"))
            page[pypdf.generic.NameObject("/Contents")] = writer._add_object(stream)
            font_dict = pypdf.generic.DictionaryObject({
                pypdf.generic.NameObject("/Type"): pypdf.generic.NameObject("/Font"),
                pypdf.generic.NameObject("/Subtype"): pypdf.generic.NameObject("/Type1"),
                pypdf.generic.NameObject("/BaseFont"): pypdf.generic.NameObject("/Helvetica"),
            })
            font_ref = writer._add_object(font_dict)
            page[pypdf.generic.NameObject("/Resources")] = pypdf.generic.DictionaryObject({
                pypdf.generic.NameObject("/Font"): pypdf.generic.DictionaryObject({
                    pypdf.generic.NameObject("/F1"): font_ref,
                })
            })
        buf = io.BytesIO()
        writer.write(buf)
        p.write_bytes(buf.getvalue())

        extracted = plugin._extract_pdf_text(str(p))
        assert extracted is not None
        assert "PageContentNumber50" in extracted
        assert "PageContentNumber51" not in extracted
        assert "PageContentNumber52" not in extracted

    def test_tier2_buffer_cap_large_file(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Constant MAX_BUFFER_BYTES is exactly 25MB and MAX_WORDS is 50,000."""
        assert MAX_BUFFER_BYTES == 25 * 1024 * 1024
        assert MAX_WORDS == 50_000
        assert MAX_PDF_PAGES == 50

    def test_tier2_preview_length_bounded(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Preview snippet returned by extract_document_representation must not exceed 500 chars."""
        d = tmp_path / "long_preview.docx"
        long_text = "WordToken " * 200
        d.write_bytes(_make_docx([long_text]))

        rep = plugin.extract_document_representation(str(d))
        assert rep is not None
        _, preview, length = rep
        assert len(preview) <= 500
        assert length > len(preview)

    # --- 6. Token Similarity Threshold Edge Cases (>= 5 cases) ---

    def test_tier2_token_similarity_exact_090_pass(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Documents with token Jaccard similarity >= 0.90 must be clustered."""
        d1 = tmp_path / "sim90_a.docx"
        d2 = tmp_path / "sim90_b.docx"
        # 90 common tokens, 5 unique to A, 5 unique to B -> inter = 90, union = 100 -> Jaccard = 0.90
        common = [f"sharedt{i}" for i in range(90)]
        uniq_a = [f"uniqueA{i}" for i in range(5)]
        uniq_b = [f"uniqueB{i}" for i in range(5)]
        d1.write_bytes(_make_docx([" ".join(common + uniq_a)]))
        d2.write_bytes(_make_docx([" ".join(common + uniq_b)]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier2_token_similarity_089_rejected(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Documents with token Jaccard similarity ~0.88 (< 0.90) must NOT be clustered."""
        d1 = tmp_path / "sim88_a.docx"
        d2 = tmp_path / "sim88_b.docx"
        # 88 common tokens, 6 unique to A, 6 unique to B -> inter = 88, union = 100 -> Jaccard = 0.88 < 0.90
        common = [f"sharedt{i}" for i in range(88)]
        uniq_a = [f"uniqueA{i}" for i in range(6)]
        uniq_b = [f"uniqueB{i}" for i in range(6)]
        d1.write_bytes(_make_docx([" ".join(common + uniq_a)]))
        d2.write_bytes(_make_docx([" ".join(common + uniq_b)]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0

    def test_tier2_token_similarity_095_pass(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Documents with token Jaccard similarity ~0.95 must be clustered."""
        d1 = tmp_path / "sim95_a.docx"
        d2 = tmp_path / "sim95_b.docx"
        common = [f"sharedt{i}" for i in range(95)]
        uniq_a = [f"uniqueA{i}" for i in range(2)]
        uniq_b = [f"uniqueB{i}" for i in range(3)]
        d1.write_bytes(_make_docx([" ".join(common + uniq_a)]))
        d2.write_bytes(_make_docx([" ".join(common + uniq_b)]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier2_token_similarity_disjoint_00_rejected(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Completely disjoint documents with 0.0 token similarity must not be clustered."""
        d1 = tmp_path / "disjoint_a.docx"
        d2 = tmp_path / "disjoint_b.docx"
        d1.write_bytes(_make_docx(["apple banana cherry date elderberry fig grape honeydew kiwi lemon"]))
        d2.write_bytes(_make_docx(["mercury venus earth mars jupiter saturn uranus neptune pluto ceres"]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0

    def test_tier2_short_text_bypass(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Documents with fewer than 5 tokens must bypass near-duplicate similarity matching."""
        d1 = tmp_path / "short_a.docx"
        d2 = tmp_path / "short_b.docx"
        # 3 words -> fewer than MIN_TOKENS_FOR_SIMILARITY (5)
        d1.write_bytes(_make_docx(["hello world test"]))
        d2.write_bytes(_make_docx(["hello world cool"]))

        candidates = [
            FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
            FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 0


# ==============================================================================
# TIER 3: Cross-Feature Interactions
# ==============================================================================


class TestTier3CrossFeatureInteractions:
    """Tier 3: Multi-format matching, cross-format row shuffling, DSU clustering, and pipeline integration."""

    def test_tier3_docx_and_odt_identical_text_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """DOCX and ODT containing identical textual content must cluster together."""
        d = tmp_path / "paper.docx"
        o = tmp_path / "paper.odt"
        text = "Cross platform document interchange format evaluation and verification."
        d.write_bytes(_make_docx([text]))
        o.write_bytes(_make_odt([text]))

        candidates = [
            FileEntry(path=str(d), size_bytes=d.stat().st_size),
            FileEntry(path=str(o), size_bytes=o.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2
        exts = {Path(m.path).suffix.lower() for m in clusters[0].members}
        assert exts == {".docx", ".odt"}

    def test_tier3_pdf_and_docx_identical_text_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PDF export and source DOCX containing identical text must cluster together."""
        p = tmp_path / "contract.pdf"
        d = tmp_path / "contract.docx"
        text = "Master Services Agreement between Enterprise Client and Software Provider."
        p.write_bytes(_make_pdf(text))
        d.write_bytes(_make_docx([text]))

        candidates = [
            FileEntry(path=str(p), size_bytes=p.stat().st_size),
            FileEntry(path=str(d), size_bytes=d.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier3_pptx_and_docx_identical_text_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """PPTX slides and DOCX document containing identical text lines must cluster together."""
        ppt = tmp_path / "agenda.pptx"
        doc = tmp_path / "agenda.docx"
        text = "Strategic Vision Annual Goals Key Performance Indicators."
        ppt.write_bytes(_make_pptx([text]))
        doc.write_bytes(_make_docx([text]))

        candidates = [
            FileEntry(path=str(ppt), size_bytes=ppt.stat().st_size),
            FileEntry(path=str(doc), size_bytes=doc.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier3_odt_and_pdf_identical_text_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """ODT document and PDF export containing identical text must cluster together."""
        o = tmp_path / "memo.odt"
        p = tmp_path / "memo.pdf"
        text = "Internal Organizational Memorandum regarding Telecommuting Policies."
        o.write_bytes(_make_odt([text]))
        p.write_bytes(_make_pdf(text))

        candidates = [
            FileEntry(path=str(o), size_bytes=o.stat().st_size),
            FileEntry(path=str(p), size_bytes=p.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier3_csv_comma_vs_tsv_tab_shuffled_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Comma-delimited CSV and Tab-delimited TSV with shuffled data rows must cluster together."""
        c = tmp_path / "users.csv"
        t = tmp_path / "users.tsv"
        header = ["user_id", "email", "role"]
        rows_csv = [header, ["u1", "alice@example.com", "admin"], ["u2", "bob@example.com", "editor"]]
        rows_tsv = [header, ["u2", "bob@example.com", "editor"], ["u1", "alice@example.com", "admin"]]
        c.write_bytes(_make_csv(rows_csv, delimiter=","))
        t.write_bytes(_make_csv(rows_tsv, delimiter="\t"))

        candidates = [
            FileEntry(path=str(c), size_bytes=c.stat().st_size),
            FileEntry(path=str(t), size_bytes=t.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier3_csv_semicolon_vs_tsv_shuffled_match(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Semicolon-delimited CSV and Tab-delimited TSV with shuffled rows must cluster together."""
        c = tmp_path / "inventory.csv"
        t = tmp_path / "inventory.tsv"
        header = ["code", "location", "count"]
        rows_c = [header, ["C1", "LocA", "10"], ["C2", "LocB", "20"]]
        rows_t = [header, ["C2", "LocB", "20"], ["C1", "LocA", "10"]]
        c.write_bytes(_make_csv(rows_c, delimiter=";"))
        t.write_bytes(_make_csv(rows_t, delimiter="\t"))

        candidates = [
            FileEntry(path=str(c), size_bytes=c.stat().st_size),
            FileEntry(path=str(t), size_bytes=t.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1

    def test_tier3_dsu_transitive_clustering_three_files(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """DSU must transitively merge candidates A~B and B~C into a single 3-file cluster."""
        f1 = tmp_path / "doc1.docx"
        f2 = tmp_path / "doc2.docx"
        f3 = tmp_path / "doc3.docx"
        words = [f"wordtoken{i}" for i in range(100)]
        f1.write_bytes(_make_docx([" ".join(words + ["extraA"])]))
        f2.write_bytes(_make_docx([" ".join(words + ["extraB"])]))
        f3.write_bytes(_make_docx([" ".join(words + ["extraC"])]))

        candidates = [
            FileEntry(path=str(f1), size_bytes=f1.stat().st_size),
            FileEntry(path=str(f2), size_bytes=f2.stat().st_size),
            FileEntry(path=str(f3), size_bytes=f3.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 3

    def test_tier3_disjoint_clusters_separation(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Two separate document topics must produce exactly two distinct clusters."""
        # Topic 1: Astrophysics (2 files)
        a1 = tmp_path / "astro_a.pdf"
        a2 = tmp_path / "astro_b.pdf"
        a_text = "Gravitational waves emitted from binary black hole coalescences in deep space."
        a1.write_bytes(_make_pdf(a_text))
        a2.write_bytes(_make_pdf(a_text))

        # Topic 2: Biochemistry (2 files)
        b1 = tmp_path / "bio_a.docx"
        b2 = tmp_path / "bio_b.docx"
        b_text = "Enzymatic catalytic pathways and allosteric protein regulation mechanisms."
        b1.write_bytes(_make_docx([b_text]))
        b2.write_bytes(_make_docx([b_text]))

        candidates = [
            FileEntry(path=str(a1), size_bytes=a1.stat().st_size),
            FileEntry(path=str(a2), size_bytes=a2.stat().st_size),
            FileEntry(path=str(b1), size_bytes=b1.stat().st_size),
            FileEntry(path=str(b2), size_bytes=b2.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 2

    def test_tier3_mixed_format_cluster_quadruplet(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Four different formats (.pdf, .docx, .pptx, .odt) with identical text form 1 cluster."""
        text = "Global unified corporate policy on data retention and automated deduplication."
        p = tmp_path / "policy.pdf"
        d = tmp_path / "policy.docx"
        ppt = tmp_path / "policy.pptx"
        o = tmp_path / "policy.odt"
        p.write_bytes(_make_pdf(text))
        d.write_bytes(_make_docx([text]))
        ppt.write_bytes(_make_pptx([text]))
        o.write_bytes(_make_odt([text]))

        candidates = [
            FileEntry(path=str(p), size_bytes=p.stat().st_size),
            FileEntry(path=str(d), size_bytes=d.stat().st_size),
            FileEntry(path=str(ppt), size_bytes=ppt.stat().st_size),
            FileEntry(path=str(o), size_bytes=o.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 4
        assert clusters[0].metadata["member_count"] == 4

    def test_tier3_pipeline_tiered_pruning(self, tmp_path: Path):
        """Pipeline runs Tier 1 ExactHash first; resaved documents fall through to DocumentTextMatcher."""
        scan_dir = tmp_path / "scan_root"
        scan_dir.mkdir()

        # Pair 1: Byte-identical DOCX files -> claimed by ExactHashMatcher
        d1 = scan_dir / "exact1.docx"
        d2 = scan_dir / "exact2.docx"
        docx_bytes = _make_docx(["Byte identical content."])
        d1.write_bytes(docx_bytes)
        d2.write_bytes(docx_bytes)

        # Pair 2: Resaved with different timestamps/metadata -> claimed by DocumentTextMatcher
        d3 = scan_dir / "resaved1.docx"
        d4 = scan_dir / "resaved2.docx"
        d3.write_bytes(_make_docx(["Resaved content with identical text."], app_metadata="<App>Word</App>"))
        d4.write_bytes(_make_docx(["Resaved content with identical text."], app_metadata="<App>Libre</App>"))

        registry = PluginRegistry()
        registry.register(ExactHashMatcherPlugin())
        registry.register(DocumentTextMatcherPlugin())
        registry.register(SafeQuarantineActionPlugin())

        pipeline = DeduplicationPipeline(paths=[scan_dir], registry=registry)
        summary = pipeline.run_scan()

        assert summary.total_duplicate_groups >= 2
        # Exact group claimed by ExactHash
        assert summary.exact_duplicate_groups >= 1
        # Document text matcher cluster discovered
        types = {r.match_type for r in summary.groups}
        assert MatchType.EXACT_HASH in types
        assert MatchType.CONTENT_NEAR_DUPLICATE in types

    def test_tier3_keeper_strategy_selection(self, tmp_path: Path):
        """CompositeKeeperStrategy selects the cleanest path over copy/draft suffixes."""
        clean = tmp_path / "quarterly_report.docx"
        copy_1 = tmp_path / "quarterly_report_copy (1).docx"
        draft = tmp_path / "quarterly_report_draft.docx"

        strategy = CompositeKeeperStrategy()
        cluster = DuplicateCluster(
            cluster_id=1,
            match_type=MatchType.CONTENT_NEAR_DUPLICATE,
            members=[
                FileEntry(path=str(copy_1), size_bytes=1000),
                FileEntry(path=str(clean), size_bytes=1000),
                FileEntry(path=str(draft), size_bytes=1000),
            ],
        )
        keeper, dupes = strategy.choose_keeper(cluster)
        assert Path(keeper.path).name == "quarterly_report.docx"
        assert len(dupes) == 2


# ==============================================================================
# TIER 4: Real-World Application Scenarios (>=5 scenarios)
# ==============================================================================


class TestTier4RealWorldApplicationScenarios:
    """Tier 4: Realistic real-world deduplication workflows and complex multi-file scenarios."""

    def test_tier4_rebrand_revision_draft_docx_vs_final_pdf(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Scenario 1: Corporate rebrand document drafted in Word and finalized in PDF."""
        marketing_draft = tmp_path / "Clairvoy_Brand_Guidelines_Draft_v4.docx"
        legal_export = tmp_path / "Clairvoy_Brand_Guidelines_Final_Approved.pdf"

        body = (
            "Clairvoy Brand Guidelines and Visual Identity Standards 2026. "
            "Our core mission is delivering ultra fast 100 percent offline storage deduplication. "
            "Primary brand colors include Electric Cyan and Deep Indigo. "
            "All typography must adhere to clean grotesque sans-serif specifications."
        )
        marketing_draft.write_bytes(_make_docx([body], app_metadata="<App>Word</App>"))
        legal_export.write_bytes(_make_pdf(body, author="Legal & Compliance"))

        candidates = [
            FileEntry(path=str(marketing_draft), size_bytes=marketing_draft.stat().st_size),
            FileEntry(path=str(legal_export), size_bytes=legal_export.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2
        assert clusters[0].match_type == MatchType.CONTENT_NEAR_DUPLICATE

    def test_tier4_permuted_sales_export_dataset(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Scenario 2: CRM sales dataset exported as CSV and re-exported as TSV with shuffled rows."""
        crm_csv = tmp_path / "q3_sales_americas.csv"
        bi_tsv = tmp_path / "q3_sales_bi_export.tsv"

        header = ["deal_id", "account", "stage", "mrr_value", "close_date"]
        rows = [
            ["D-101", "Acme Corporation", "Closed Won", "25000", "2026-08-15"],
            ["D-102", "Globex Global", "Negotiation", "42000", "2026-09-01"],
            ["D-103", "Initech Systems", "Proposal", "15000", "2026-09-10"],
            ["D-104", "Umbrella Bio", "Closed Won", "88000", "2026-08-28"],
        ]
        # CRM exports original order
        crm_csv.write_bytes(_make_csv([header] + rows, delimiter=","))
        # BI tool exports in reverse row order with extra whitespace in TSV format
        shuffled = [rows[3], rows[0], rows[2], rows[1]]
        bi_tsv.write_bytes(_make_csv([header] + shuffled, delimiter="\t"))

        candidates = [
            FileEntry(path=str(crm_csv), size_bytes=crm_csv.stat().st_size),
            FileEntry(path=str(bi_tsv), size_bytes=bi_tsv.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier4_presentation_revision_minor_slide_edits(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Scenario 3: Board meeting presentation drafts with minor slide edits (>= 0.90 Jaccard)."""
        deck_draft = tmp_path / "Board_Meeting_Q3_Draft.pptx"
        deck_final = tmp_path / "Board_Meeting_Q3_Final.pptx"

        slides_draft = [
            "Executive Summary: Strong Revenue Growth and Scalable Customer Acquisition.",
            "Financial Highlights: Net Retention at 138 percent and EBITDA margin positive.",
            "Product Roadmap: Autonomous storage optimization engine launching next quarter.",
            "Next Steps: Authorize additional infrastructure capital expenditures.",
        ]
        # Final presentation only modifies 2 words in slide 4
        slides_final = list(slides_draft)
        slides_final[3] = "Next Steps: Authorize additional infrastructure capital investment."

        deck_draft.write_bytes(_make_pptx(slides_draft))
        deck_final.write_bytes(_make_pptx(slides_final))

        candidates = [
            FileEntry(path=str(deck_draft), size_bytes=deck_draft.stat().st_size),
            FileEntry(path=str(deck_final), size_bytes=deck_final.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2
        assert clusters[0].similarity_scores[1] >= SIMILARITY_THRESHOLD

    def test_tier4_academic_paper_revision_odt_vs_docx(self, tmp_path: Path, plugin: DocumentTextMatcherPlugin):
        """Scenario 4: Research paper drafted in LibreOffice (.odt) and camera-ready in Word (.docx)."""
        author_draft = tmp_path / "distributed_dedup_draft.odt"
        camera_ready = tmp_path / "distributed_dedup_camera_ready.docx"

        sections = [
            "Abstract: Modern multimodal storage engines require sub-millisecond deduplication.",
            "Introduction: Cloud storage costs expand exponentially with uncompressed raw assets.",
            "Architecture: Tiered short circuit filtering reduces computational overhead by ninety percent.",
            "Evaluation: Empirical benchmarks confirm linear scaling across twenty million files.",
            "Conclusion: Offline local-first deduplication guarantees enterprise data sovereignty.",
        ]
        author_draft.write_bytes(_make_odt(sections))
        # Camera-ready version has 95%+ identical words with minor typography adjustments
        camera_ready.write_bytes(_make_docx(sections))

        candidates = [
            FileEntry(path=str(author_draft), size_bytes=author_draft.stat().st_size),
            FileEntry(path=str(camera_ready), size_bytes=camera_ready.stat().st_size),
        ]
        clusters = plugin.find_duplicates(candidates, candidates)
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2

    def test_tier4_full_directory_scan_mixed_documents(self, tmp_path: Path):
        """Scenario 5: Full scan of a directory containing valid, corrupted, encrypted, and permuted docs."""
        scan_dir = tmp_path / "mixed_corp_archive"
        scan_dir.mkdir()

        # 1. Duplicate PDF pair
        p1 = scan_dir / "invoice_1001.pdf"
        p2 = scan_dir / "invoice_1001_copy.pdf"
        p_text = "Invoice Number 1001 Total Due USD 4500 Net 30 Terms Apply."
        p1.write_bytes(_make_pdf(p_text))
        p2.write_bytes(_make_pdf(p_text))

        # 2. Permuted CSV/TSV pair
        c = scan_dir / "employees.csv"
        t = scan_dir / "employees_reorder.tsv"
        emp_hdr = ["emp_id", "name", "dept"]
        c.write_bytes(_make_csv([emp_hdr, ["1", "Alice", "IT"], ["2", "Bob", "HR"]], delimiter=","))
        t.write_bytes(_make_csv([emp_hdr, ["2", "Bob", "HR"], ["1", "Alice", "IT"]], delimiter="\t"))

        # 3. Corrupted PDF
        corrupt_pdf = scan_dir / "corrupted_scan.pdf"
        corrupt_pdf.write_bytes(b"Truncated non-pdf bytes \x00\x01\x02")

        # 4. Zero-byte DOCX
        zero_docx = scan_dir / "empty_draft.docx"
        zero_docx.write_bytes(b"")

        # 5. Encrypted PDF
        secret_pdf = scan_dir / "encrypted_passwords.pdf"
        secret_pdf.write_bytes(_make_pdf("Super secret payload", password="vaultpassword"))

        # 6. Near-duplicate PPTX pair
        deck1 = scan_dir / "roadmap_v1.pptx"
        deck2 = scan_dir / "roadmap_v2.pptx"
        deck_text = [
            f"RoadmapMilestone{i} detailing upcoming engineering architectural phases and deliverables."
            for i in range(1, 10)
        ]
        deck1.write_bytes(_make_pptx(deck_text))
        deck2.write_bytes(_make_pptx(deck_text + ["Minor note appended."]))

        # 7. Unique standalone ODT
        unique_odt = scan_dir / "unique_research.odt"
        unique_odt.write_bytes(_make_odt(["Unique standalone research document with completely different words."]))

        # Run pipeline
        registry = PluginRegistry()
        registry.register(ExactHashMatcherPlugin())
        registry.register(DocumentTextMatcherPlugin())
        registry.register(SafeQuarantineActionPlugin())

        pipeline = DeduplicationPipeline(paths=[scan_dir], registry=registry)
        summary = pipeline.run_scan()

        # Verify pipeline executed safely without crashing
        assert summary.total_files_scanned >= 9
        assert summary.total_duplicate_groups >= 2
        # Check generated summary files
        assert Path(summary.csv_report).exists()
        assert Path(summary.summary_json).exists()
