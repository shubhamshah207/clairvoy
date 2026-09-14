"""Unit tests for DocumentTextMatcherPlugin (.pdf, .docx, .pptx, .odt, .csv, .tsv)."""

import csv
import io
import zipfile
from pathlib import Path

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.plugins.document_matcher import (
    MAX_WORDS,
    SUPPORTED_DOCUMENT_EXTENSIONS,
    DocumentTextMatcherPlugin,
)


def _make_dummy_docx(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>"
            "</w:document>"
        )
        zf.writestr("word/document.xml", xml.encode("utf-8"))
    return buf.getvalue()


def _make_dummy_pptx(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f"<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>"
            "</p:sld>"
        )
        zf.writestr("ppt/slides/slide1.xml", xml.encode("utf-8"))
    return buf.getvalue()


def _make_dummy_odt(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
            f"<office:body><office:text><text:p>{text}</text:p></office:text></office:body>"
            "</office:document-content>"
        )
        zf.writestr("content.xml", xml.encode("utf-8"))
    return buf.getvalue()


def _make_synthetic_pdf(text: str) -> bytes:
    safe_text = text.replace("(", "").replace(")", "").replace("\\", "")
    content_stream = f"BT\n/F1 12 Tf\n10 50 Td\n({safe_text}) Tj\nET\n".encode()
    stream_len = len(content_stream)
    pdf_parts = [
        b"%PDF-1.4\n",
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode()
        + content_stream
        + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    body = b"".join(pdf_parts)
    xref_offset = len(body)
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for i in range(1, 6):
        part_offset = len(b"".join(pdf_parts[:i]))
        xref += f"{part_offset:010d} 00000 n \n".encode("ascii")
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    return body + xref + trailer


def test_supported_document_extensions():
    assert ".pdf" in SUPPORTED_DOCUMENT_EXTENSIONS
    assert ".docx" in SUPPORTED_DOCUMENT_EXTENSIONS
    assert ".pptx" in SUPPORTED_DOCUMENT_EXTENSIONS
    assert ".odt" in SUPPORTED_DOCUMENT_EXTENSIONS
    assert ".csv" in SUPPORTED_DOCUMENT_EXTENSIONS
    assert ".tsv" in SUPPORTED_DOCUMENT_EXTENSIONS


def test_document_matcher_availability():
    plugin = DocumentTextMatcherPlugin()
    avail, reason = plugin.is_available()
    assert avail is True
    assert "available" in reason.lower()


def test_filter_supported():
    plugin = DocumentTextMatcherPlugin()
    files = [
        FileEntry(path="/path/to/doc.docx", size_bytes=1024),
        FileEntry(path="/path/to/data.csv", size_bytes=2048),
        FileEntry(path="/path/to/empty.pdf", size_bytes=0),
        FileEntry(path="/path/to/photo.jpg", size_bytes=4096),
        FileEntry(path="/path/to/notes.txt", size_bytes=512),
    ]
    supported = plugin.filter_supported(files)
    paths = [f.path for f in supported]
    assert "/path/to/doc.docx" in paths
    assert "/path/to/data.csv" in paths
    assert "/path/to/empty.pdf" not in paths
    assert "/path/to/photo.jpg" not in paths
    assert "/path/to/notes.txt" not in paths


def test_docx_duplicate_matching(tmp_path: Path):
    doc1 = tmp_path / "original.docx"
    doc2 = tmp_path / "copy_resaved.docx"
    text = "The quick brown fox jumps over the lazy dog and explores the meadow."
    doc1.write_bytes(_make_dummy_docx(text))
    # Resaved with extra timestamp or metadata but identical text
    doc2.write_bytes(_make_dummy_docx(text + "   \n"))

    plugin = DocumentTextMatcherPlugin()
    candidates = [
        FileEntry(path=str(doc1), size_bytes=doc1.stat().st_size),
        FileEntry(path=str(doc2), size_bytes=doc2.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert clusters[0].match_type == MatchType.CONTENT_NEAR_DUPLICATE
    assert len(clusters[0].members) == 2


def test_pptx_duplicate_matching(tmp_path: Path):
    ppt1 = tmp_path / "slides1.pptx"
    ppt2 = tmp_path / "slides2.pptx"
    text = "Quarterly Business Review and Strategic Growth Objectives 2026."
    ppt1.write_bytes(_make_dummy_pptx(text))
    ppt2.write_bytes(_make_dummy_pptx(text))

    plugin = DocumentTextMatcherPlugin()
    candidates = [
        FileEntry(path=str(ppt1), size_bytes=ppt1.stat().st_size),
        FileEntry(path=str(ppt2), size_bytes=ppt2.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert clusters[0].match_type == MatchType.CONTENT_NEAR_DUPLICATE


def test_odt_duplicate_matching(tmp_path: Path):
    odt1 = tmp_path / "report_draft.odt"
    odt2 = tmp_path / "report_final.odt"
    text = "Comprehensive OpenDocument specification report for deduplication validation."
    odt1.write_bytes(_make_dummy_odt(text))
    odt2.write_bytes(_make_dummy_odt(text + "   \t"))

    plugin = DocumentTextMatcherPlugin()
    candidates = [
        FileEntry(path=str(odt1), size_bytes=odt1.stat().st_size),
        FileEntry(path=str(odt2), size_bytes=odt2.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert clusters[0].match_type == MatchType.CONTENT_NEAR_DUPLICATE
    assert len(clusters[0].members) == 2


def test_csv_permutation_invariant_matching(tmp_path: Path):
    csv1 = tmp_path / "data_a.csv"
    csv2 = tmp_path / "data_b.csv"

    rows_a = [
        ["id", "name", "score"],
        ["1", "Alice", "95"],
        ["2", "Bob", "88"],
        ["3", "Charlie", "92"],
    ]
    # Reordered rows but identical data
    rows_b = [
        ["id", "name", "score"],
        ["3", "Charlie", "92"],
        ["1", "Alice", "95"],
        ["2", "Bob", "88"],
    ]

    with open(csv1, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows_a)
    with open(csv2, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows_b)

    plugin = DocumentTextMatcherPlugin()
    candidates = [
        FileEntry(path=str(csv1), size_bytes=csv1.stat().st_size),
        FileEntry(path=str(csv2), size_bytes=csv2.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert clusters[0].match_type == MatchType.CONTENT_NEAR_DUPLICATE


def test_tsv_and_cross_format_tabular_matching(tmp_path: Path):
    tsv1 = tmp_path / "records_a.tsv"
    tsv2 = tmp_path / "records_b.tsv"
    csv_file = tmp_path / "records_c.csv"

    rows = [
        ["dept", "emp_id", "salary"],
        ["Engineering", "E101", "120000"],
        ["Marketing", "M202", "95000"],
        ["Sales", "S303", "105000"],
    ]
    rows_shuffled = [
        ["dept", "emp_id", "salary"],
        ["Sales", "S303", "105000"],
        ["Engineering", "E101", "120000"],
        ["Marketing", "M202", "95000"],
    ]

    with open(tsv1, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter="\t").writerows(rows)
    with open(tsv2, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter="\t").writerows(rows_shuffled)
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=",").writerows(rows_shuffled)

    plugin = DocumentTextMatcherPlugin()
    candidates = [
        FileEntry(path=str(tsv1), size_bytes=tsv1.stat().st_size),
        FileEntry(path=str(tsv2), size_bytes=tsv2.stat().st_size),
        FileEntry(path=str(csv_file), size_bytes=csv_file.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 3


def test_synthetic_pdf_extraction_and_matching(tmp_path: Path):
    pdf1 = tmp_path / "doc1.pdf"
    pdf2 = tmp_path / "doc2.pdf"
    text = "Machine learning inference pipeline for storage efficiency and deduplication"
    pdf1.write_bytes(_make_synthetic_pdf(text))
    pdf2.write_bytes(_make_synthetic_pdf(text))

    plugin = DocumentTextMatcherPlugin()
    rep = plugin.extract_document_representation(str(pdf1))
    assert rep is not None
    content_hash, preview, length = rep
    assert len(content_hash) == 64
    assert "inference" in preview.lower()

    candidates = [
        FileEntry(path=str(pdf1), size_bytes=pdf1.stat().st_size),
        FileEntry(path=str(pdf2), size_bytes=pdf2.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 2


def test_pdf_extraction_if_sample_exists():
    real_pdf = Path("/mnt/e/ApartmentRelated/2022/Renter'sInsurance.pdf")
    if real_pdf.is_file():
        plugin = DocumentTextMatcherPlugin()
        rep = plugin.extract_document_representation(str(real_pdf))
        assert rep is not None
        content_hash, preview, length = rep
        assert len(content_hash) == 64
        assert length > 500
        assert "insurance" in preview.lower()


def test_near_duplicate_token_jaccard_matching(tmp_path: Path):
    doc1 = tmp_path / "v1.docx"
    doc2 = tmp_path / "v2.docx"
    doc_other = tmp_path / "v_other.docx"

    # 50 words baseline
    base_words = [f"word{i}" for i in range(50)]
    # v1 has 50 words
    # v2 has 47 of the same words + 3 different words (Jaccard = 47 / 53 = 0.8868, wait: let's do 48 same + 2 different: 48/52 = 0.923 >= 0.90)
    words_v1 = base_words[:]
    words_v2 = base_words[:48] + ["noveltermalpha", "noveltermbeta"]
    # v_other has mostly different words
    words_other = [f"differentitem{i}" for i in range(50)]

    doc1.write_bytes(_make_dummy_docx(" ".join(words_v1)))
    doc2.write_bytes(_make_dummy_docx(" ".join(words_v2)))
    doc_other.write_bytes(_make_dummy_docx(" ".join(words_other)))

    plugin = DocumentTextMatcherPlugin()
    candidates = [
        FileEntry(path=str(doc1), size_bytes=doc1.stat().st_size),
        FileEntry(path=str(doc2), size_bytes=doc2.stat().st_size),
        FileEntry(path=str(doc_other), size_bytes=doc_other.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 2
    matched_paths = [m.path for m in clusters[0].members]
    assert str(doc1) in matched_paths
    assert str(doc2) in matched_paths
    assert str(doc_other) not in matched_paths


def test_corrupted_documents_graceful_handling(tmp_path: Path):
    corrupt_docx = tmp_path / "corrupt.docx"
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_csv = tmp_path / "corrupt.csv"
    empty_docx = tmp_path / "empty.docx"

    corrupt_docx.write_bytes(b"This is definitely not a zip file.")
    corrupt_pdf.write_bytes(b"Not a valid PDF header garbage bytes \x00\xff")
    corrupt_csv.write_bytes(b"col1,col2\nval1,\x00\x01\x02binarygarbage")
    empty_docx.write_bytes(b"")

    plugin = DocumentTextMatcherPlugin()
    assert plugin.extract_document_representation(str(corrupt_docx)) is None
    assert plugin.extract_document_representation(str(corrupt_pdf)) is None
    assert plugin.extract_document_representation(str(corrupt_csv)) is None
    assert plugin.extract_document_representation(str(empty_docx)) is None

    candidates = [
        FileEntry(path=str(corrupt_docx), size_bytes=corrupt_docx.stat().st_size),
        FileEntry(path=str(corrupt_pdf), size_bytes=corrupt_pdf.stat().st_size),
        FileEntry(path=str(corrupt_csv), size_bytes=corrupt_csv.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 0


def test_word_cap_truncation(tmp_path: Path):
    large_doc = tmp_path / "massive.docx"
    # Generate 60,000 words
    words = [f"token{i}" for i in range(60_000)]
    large_doc.write_bytes(_make_dummy_docx(" ".join(words)))

    plugin = DocumentTextMatcherPlugin()
    rep = plugin.extract_document_representation(str(large_doc))
    assert rep is not None
    content_hash, preview, length = rep
    assert len(content_hash) == 64

    # The extracted text should contain token0 and token49999, but not token50001
    assert "token0" in preview
    # Verify internal word cap behavior
    data = plugin._extract_document_data(str(large_doc))
    assert data is not None
    token_set = data[3]
    assert len(token_set) == MAX_WORDS


def test_multi_cluster_grouping(tmp_path: Path):
    # Two docx matching
    d1 = tmp_path / "a1.docx"
    d2 = tmp_path / "a2.docx"
    d1.write_bytes(_make_dummy_docx("Shared document alpha content."))
    d2.write_bytes(_make_dummy_docx("Shared document alpha content."))

    # Two pptx matching
    p1 = tmp_path / "b1.pptx"
    p2 = tmp_path / "b2.pptx"
    p1.write_bytes(_make_dummy_pptx("Shared slide beta content."))
    p2.write_bytes(_make_dummy_pptx("Shared slide beta content."))

    # One unique odt
    u = tmp_path / "unique.odt"
    u.write_bytes(_make_dummy_odt("Completely distinct unique text gamma."))

    plugin = DocumentTextMatcherPlugin()
    candidates = [
        FileEntry(path=str(d1), size_bytes=d1.stat().st_size),
        FileEntry(path=str(d2), size_bytes=d2.stat().st_size),
        FileEntry(path=str(p1), size_bytes=p1.stat().st_size),
        FileEntry(path=str(p2), size_bytes=p2.stat().st_size),
        FileEntry(path=str(u), size_bytes=u.stat().st_size),
    ]

    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 2
    cluster_member_paths = [{m.path for m in c.members} for c in clusters]
    assert {str(d1), str(d2)} in cluster_member_paths
    assert {str(p1), str(p2)} in cluster_member_paths


def test_document_surrogate_characters_handling(tmp_path: Path, monkeypatch):
    """Verifies that PDF or document text containing isolated Unicode surrogate characters does not crash."""
    plugin = DocumentTextMatcherPlugin()
    doc = tmp_path / "surrogate.pdf"
    doc.write_bytes(b"%PDF-1.4 dummy mock content")

    # Mock _extract_pdf_text returning a string containing surrogate character \ud835
    monkeypatch.setattr(plugin, "_extract_pdf_text", lambda p: "Math symbol \ud835 section header text")

    # Must extract without raising UnicodeEncodeError
    res = plugin._extract_document_data(str(doc))
    assert res is not None
    content_hash, preview, length, tokens = res
    assert isinstance(content_hash, str)
    assert len(content_hash) == 64
    assert "math" in tokens

