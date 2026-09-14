"""Empirical adversarial stress tests for Milestone M1 (DocumentTextMatcherPlugin).

Authored by challenger_m1_2.
Focus areas:
1. Cross-format identical and near-duplicate matching (.odt, .docx, .pptx, .pdf)
2. Multi-page PDF 50-page strict ceiling enforcement
3. Memory bounds & buffer capping (25 MB stream limit, zip-bomb safety)
4. Strict 100% offline local-first invariant (no socket connections)
5. Multi-threaded concurrency safety
"""

import concurrent.futures
import io
import socket
import xml.sax.saxutils
import zipfile
from pathlib import Path

import pypdf

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.plugins.document_matcher import (
    MAX_BUFFER_BYTES,
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


def test_adversarial_cross_format_four_way_clustering(tmp_path: Path):
    """Verify that .docx, .pptx, .odt, and .pdf with identical text cluster into 1 cluster."""
    common_text = (
        "Executive quarterly summary: operational revenue increased by twenty percent "
        "across all domestic and international business units during fiscal year 2026."
    )
    plugin = DocumentTextMatcherPlugin()

    docx_path = tmp_path / "report.docx"
    pptx_path = tmp_path / "presentation.pptx"
    odt_path = tmp_path / "document.odt"
    pdf_path = tmp_path / "export.pdf"

    docx_path.write_bytes(_make_dummy_docx(common_text))
    pptx_path.write_bytes(_make_dummy_pptx(common_text))
    odt_path.write_bytes(_make_dummy_odt(common_text))
    pdf_path.write_bytes(_make_synthetic_pdf(common_text))

    entries = [
        FileEntry(path=str(p), size_bytes=p.stat().st_size)
        for p in [docx_path, pptx_path, odt_path, pdf_path]
    ]

    # Verify representations have identical content hashes
    reps = [plugin.extract_document_representation(e.path) for e in entries]
    assert all(r is not None for r in reps)
    hashes = {r[0] for r in reps if r is not None}
    assert len(hashes) == 1, f"Expected 1 unique hash across 4 formats, got {len(hashes)}"

    clusters = plugin.find_duplicates(entries, entries)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.match_type == MatchType.CONTENT_NEAR_DUPLICATE
    assert len(cluster.members) == 4
    exts = cluster.metadata.get("extensions", [])
    assert sorted(exts) == [".docx", ".odt", ".pdf", ".pptx"]
    assert all(score == 1.0 for score in cluster.similarity_scores)


def test_adversarial_cross_format_near_duplicate_detection(tmp_path: Path):
    """Verify that .docx and .odt with Jaccard token similarity >= 0.90 cluster together."""
    base_words = [f"tokenterm_{i}" for i in range(50)]
    docx_text = " ".join(base_words)
    # 48 common tokens + 2 novel tokens => 48 / 52 = 0.923 >= 0.90
    odt_text = " ".join(base_words[:48] + ["novelextraalpha", "novelextrabeta"])

    f_docx = tmp_path / "source.docx"
    f_odt = tmp_path / "variant.odt"

    f_docx.write_bytes(_make_dummy_docx(docx_text))
    f_odt.write_bytes(_make_dummy_odt(odt_text))

    entries = [
        FileEntry(path=str(f_docx), size_bytes=f_docx.stat().st_size),
        FileEntry(path=str(f_odt), size_bytes=f_odt.stat().st_size),
    ]

    plugin = DocumentTextMatcherPlugin()
    clusters = plugin.find_duplicates(entries, entries)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert len(cluster.members) == 2
    assert sorted(cluster.metadata.get("extensions", [])) == [".docx", ".odt"]
    # Similarity score should be ~0.923
    assert cluster.similarity_scores[1] >= 0.90


def test_adversarial_cross_format_dissimilar_rejection(tmp_path: Path):
    """Verify that .docx and .odt with Jaccard token similarity < 0.90 are not clustered."""
    base_words = [f"tokenterm_{i}" for i in range(50)]
    docx_text = " ".join(base_words)
    # 40 common tokens + 10 novel tokens => 40 / 60 = 0.667 < 0.90
    odt_text = " ".join(base_words[:40] + [f"divergent_{i}" for i in range(10)])

    f_docx = tmp_path / "source.docx"
    f_odt = tmp_path / "unrelated.odt"

    f_docx.write_bytes(_make_dummy_docx(docx_text))
    f_odt.write_bytes(_make_dummy_odt(odt_text))

    entries = [
        FileEntry(path=str(f_docx), size_bytes=f_docx.stat().st_size),
        FileEntry(path=str(f_odt), size_bytes=f_odt.stat().st_size),
    ]

    plugin = DocumentTextMatcherPlugin()
    clusters = plugin.find_duplicates(entries, entries)
    assert len(clusters) == 0


def test_adversarial_multilingual_cross_format_matching(tmp_path: Path):
    """Verify that Unicode and multilingual text match identically across .docx and .odt."""
    raw_text = "Überraschung! 東京 Déjà vu: 2026年 財務諸表と年次報告書の重複検証"
    escaped_text = xml.sax.saxutils.escape(raw_text)

    f_docx = tmp_path / "unicode.docx"
    f_odt = tmp_path / "unicode.odt"

    f_docx.write_bytes(_make_dummy_docx(escaped_text))
    f_odt.write_bytes(_make_dummy_odt(escaped_text))

    entries = [
        FileEntry(path=str(f_docx), size_bytes=f_docx.stat().st_size),
        FileEntry(path=str(f_odt), size_bytes=f_odt.stat().st_size),
    ]

    plugin = DocumentTextMatcherPlugin()
    rep1 = plugin.extract_document_representation(str(f_docx))
    rep2 = plugin.extract_document_representation(str(f_odt))
    assert rep1 is not None and rep2 is not None
    assert rep1[0] == rep2[0]

    clusters = plugin.find_duplicates(entries, entries)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 2


def test_adversarial_pdf_strict_50_page_cap(tmp_path: Path):
    """Verify that PDF parsing caps strictly at 50 pages and ignores pages 51+."""
    writer75 = pypdf.PdfWriter()
    writer50 = pypdf.PdfWriter()

    # Pages 0..49: standard content
    for i in range(50):
        content = f"StandardDocumentContentForPage_{i}"
        pdf_bytes = _make_synthetic_pdf(content)
        r = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        writer50.add_page(r.pages[0])
        writer75.add_page(r.pages[0])

    # Pages 50..74: secret content in writer75
    for i in range(50, 75):
        content = f"EXCLUDED_SECRET_TOKEN_{i}"
        pdf_bytes = _make_synthetic_pdf(content)
        r = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        writer75.add_page(r.pages[0])

    pdf50_path = tmp_path / "doc_50_pages.pdf"
    pdf75_path = tmp_path / "doc_75_pages.pdf"

    with open(pdf50_path, "wb") as f:
        writer50.write(f)

    with open(pdf75_path, "wb") as f:
        writer75.write(f)

    plugin = DocumentTextMatcherPlugin()

    # Check extracted data
    data75 = plugin._extract_document_data(str(pdf75_path))
    assert data75 is not None
    tokens75 = data75[3]

    # Verify first 50 pages are extracted
    assert "standarddocumentcontentforpage_0" in tokens75
    assert "standarddocumentcontentforpage_49" in tokens75

    # Verify pages 50..74 are NOT extracted
    assert "excluded_secret_token_50" not in tokens75
    assert "excluded_secret_token_74" not in tokens75

    # Verify 50-page PDF and 75-page PDF produce identical hash and cluster together
    rep50 = plugin.extract_document_representation(str(pdf50_path))
    rep75 = plugin.extract_document_representation(str(pdf75_path))
    assert rep50 is not None and rep75 is not None
    assert rep50[0] == rep75[0]

    e50 = FileEntry(path=str(pdf50_path), size_bytes=pdf50_path.stat().st_size)
    e75 = FileEntry(path=str(pdf75_path), size_bytes=pdf75_path.stat().st_size)
    clusters = plugin.find_duplicates([e50, e75], [e50, e75])
    assert len(clusters) == 1
    assert len(clusters[0].members) == 2


def test_adversarial_buffer_bounds_oversized_csv(tmp_path: Path):
    """Verify that a >25 MB CSV file is safely capped at MAX_BUFFER_BYTES without memory failure."""
    csv_path = tmp_path / "massive_dataset.csv"
    # Generate 700,000 lines -> ~26.5 MB
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("row_id,col_alpha,col_beta,col_gamma\n")
        for i in range(700_000):
            f.write(f"{i},data_point_alpha_{i},data_point_beta_{i},data_point_gamma_{i}\n")

    assert csv_path.stat().st_size > MAX_BUFFER_BYTES

    plugin = DocumentTextMatcherPlugin()
    rep = plugin.extract_document_representation(str(csv_path))
    assert rep is not None
    content_hash, preview, length = rep
    assert len(content_hash) == 64
    assert length > 0


def test_adversarial_buffer_bounds_oversized_xml_docx(tmp_path: Path):
    """Verify that a DOCX with uncompressed XML > 25 MB degrades gracefully without crashing."""
    docx_path = tmp_path / "zipbomb_candidate.docx"
    chunk = "<w:p><w:r><w:t>Overly repeating paragraph content in XML stream.</w:t></w:r></w:p>"
    xml_head = '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
    xml_tail = "</w:body></w:document>"

    with (
        zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf,
        zf.open("word/document.xml", "w") as xml_out,
    ):
        xml_out.write(xml_head.encode("utf-8"))
        p_bytes = chunk.encode("utf-8")
        for _ in range(320_000):
            xml_out.write(p_bytes)
        xml_out.write(xml_tail.encode("utf-8"))

    with zipfile.ZipFile(docx_path, "r") as zf:
        info = zf.getinfo("word/document.xml")
        assert info.file_size > MAX_BUFFER_BYTES

    plugin = DocumentTextMatcherPlugin()
    # When word/document.xml > 25 MB, stream read is capped at 25 MB.
    # Truncated XML raises ParseError and gracefully returns None without crashing.
    rep = plugin.extract_document_representation(str(docx_path))
    assert rep is None


def test_adversarial_offline_socket_isolation(tmp_path: Path):
    """Verify that no network sockets or external connections are opened under any operation."""
    def forbidden_socket(*args, **kwargs):
        raise RuntimeError("FORBIDDEN_NETWORK_SOCKET_ATTEMPT")

    orig_socket = socket.socket
    orig_create_connection = socket.create_connection

    socket.socket = forbidden_socket
    socket.create_connection = forbidden_socket

    try:
        plugin = DocumentTextMatcherPlugin()
        avail, reason = plugin.is_available()
        assert avail is True

        text = "100 percent offline verification test string across all supported modalities."
        d_docx = tmp_path / "offline.docx"
        d_pptx = tmp_path / "offline.pptx"
        d_odt = tmp_path / "offline.odt"
        d_pdf = tmp_path / "offline.pdf"
        d_csv = tmp_path / "offline.csv"
        d_tsv = tmp_path / "offline.tsv"

        d_docx.write_bytes(_make_dummy_docx(text))
        d_pptx.write_bytes(_make_dummy_pptx(text))
        d_odt.write_bytes(_make_dummy_odt(text))
        d_pdf.write_bytes(_make_synthetic_pdf(text))
        d_csv.write_text("header1,header2\nval1,val2\n", encoding="utf-8")
        d_tsv.write_text("header1\theader2\nval1\tval2\n", encoding="utf-8")

        entries = [
            FileEntry(path=str(p), size_bytes=p.stat().st_size)
            for p in [d_docx, d_pptx, d_odt, d_pdf, d_csv, d_tsv]
        ]

        # Ensure representation extraction does not touch network
        for e in entries:
            rep = plugin.extract_document_representation(e.path)
            assert rep is not None

        # Ensure clustering does not touch network
        clusters = plugin.find_duplicates(entries, entries)
        assert len(clusters) >= 1
    finally:
        socket.socket = orig_socket
        socket.create_connection = orig_create_connection


def test_adversarial_concurrent_thread_safety(tmp_path: Path):
    """Verify that concurrent threads accessing the shared plugin instance execute without corruption."""
    plugin = DocumentTextMatcherPlugin()

    def worker_task(idx: int) -> bool:
        t_dir = tmp_path / f"thread_{idx}"
        t_dir.mkdir(parents=True, exist_ok=True)
        f_docx = t_dir / f"thread_{idx}.docx"
        f_odt = t_dir / f"thread_{idx}.odt"
        content = f"Concurrent stress payload for thread index {idx} with unique identifiers."
        f_docx.write_bytes(_make_dummy_docx(content))
        f_odt.write_bytes(_make_dummy_odt(content))

        e1 = FileEntry(path=str(f_docx), size_bytes=f_docx.stat().st_size)
        e2 = FileEntry(path=str(f_odt), size_bytes=f_odt.stat().st_size)

        rep1 = plugin.extract_document_representation(str(f_docx))
        rep2 = plugin.extract_document_representation(str(f_odt))
        assert rep1 is not None and rep2 is not None
        assert rep1[0] == rep2[0]

        clusters = plugin.find_duplicates([e1, e2], [e1, e2])
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(worker_task, range(16)))

    assert all(results)
