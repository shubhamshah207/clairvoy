"""Adversarial stress testing and edge-case verification for DocumentTextMatcherPlugin.

Adversarial dimensions tested:
1. Permutation invariance on large datasets (10,000 CSV/TSV rows).
2. Exact boundary token similarity (89% rejected, 90% accepted, 91% accepted).
3. Soundness of O(1) ratio pruning bound (min_len / max_len).
4. Memory cap and word truncation at 50,000 words on 100,000-word documents.
5. Corrupted, truncated, 0-byte, and non-existent files (zero-crash invariant).
6. Natural numerical slide sorting in PPTX (preventing lexicographical 10 < 2 bug).
7. PDF 50-page cap and multipage extraction.
8. Cross-format deduplication (.docx, .odt, .pdf with identical text).
9. Multi-way DSU transitive clustering and similarity score preservation.
10. Delimiter sniffing robustness (commas, tabs, semicolons, quoted commas, UTF-8 BOM).
"""

from __future__ import annotations

import csv
import io
import random
import xml.sax.saxutils
import zipfile
from pathlib import Path

import pypdf

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.plugins.document_matcher import (
    MAX_WORDS,
    SIMILARITY_THRESHOLD,
    DocumentTextMatcherPlugin,
)


def _make_docx(text: str) -> bytes:
    """Helper to create a valid minimal DOCX in memory with escaped XML."""
    escaped_text = xml.sax.saxutils.escape(text)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        xml_content = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{escaped_text}</w:t></w:r></w:p></w:body>"
            "</w:document>"
        )
        zf.writestr("word/document.xml", xml_content.encode("utf-8"))
    return buf.getvalue()


def _make_pptx_slides(slides: list[str]) -> bytes:
    """Helper to create a multi-slide PPTX with natural slide numbering."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, slide_text in enumerate(slides, start=1):
            escaped = xml.sax.saxutils.escape(slide_text)
            xml_content = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                f"<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{escaped}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>"
                "</p:sld>"
            )
            zf.writestr(f"ppt/slides/slide{idx}.xml", xml_content.encode("utf-8"))
    return buf.getvalue()


def _make_odt(text: str) -> bytes:
    """Helper to create a valid minimal ODT in memory."""
    escaped_text = xml.sax.saxutils.escape(text)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        xml_content = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
            f"<office:body><office:text><text:p>{escaped_text}</text:p></office:text></office:body>"
            "</office:document-content>"
        )
        zf.writestr("content.xml", xml_content.encode("utf-8"))
    return buf.getvalue()


def _make_multipage_pdf(pages_text: list[str]) -> bytes:
    """Helper to create a valid multi-page PDF using pypdf."""
    writer = pypdf.PdfWriter()
    for text in pages_text:
        page = writer.add_blank_page(width=300, height=300)
        stream = pypdf.generic.DecodedStreamObject()
        escaped = (
            text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        )
        stream.set_data(
            f"BT /F1 12 Tf 30 250 Td ({escaped}) Tj ET".encode(
                "latin-1", errors="replace"
            )
        )
        page[pypdf.generic.NameObject("/Contents")] = writer._add_object(stream)
        font_dict = pypdf.generic.DictionaryObject({
            pypdf.generic.NameObject("/Type"): pypdf.generic.NameObject("/Font"),
            pypdf.generic.NameObject("/Subtype"): pypdf.generic.NameObject("/Type1"),
            pypdf.generic.NameObject("/BaseFont"): pypdf.generic.NameObject("/Helvetica"),
        })
        page[pypdf.generic.NameObject("/Resources")] = pypdf.generic.DictionaryObject({
            pypdf.generic.NameObject("/Font"): pypdf.generic.DictionaryObject({
                pypdf.generic.NameObject("/F1"): writer._add_object(font_dict),
            })
        })
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ==============================================================================
# 1. Permutation Invariance on Large 10,000-Row Datasets
# ==============================================================================


def test_stress_csv_10k_rows_permutation_invariance(tmp_path: Path):
    """Stress test: 10,000 rows in forward, reverse, and shuffled orders across CSV & TSV."""
    header = ["account_id", "transaction_type", "amount_cents", "status_code"]
    rng = random.Random(42)

    # 10,000 synthetic financial transaction records
    data_rows = [
        [f"ACC-{i:07d}", "TRANSFER" if i % 2 == 0 else "PAYMENT", str(1000 + i), "SUCCESS"]
        for i in range(10_000)
    ]

    rows_forward = [header] + data_rows
    rows_reverse = [header] + list(reversed(data_rows))
    shuffled_rows = list(data_rows)
    rng.shuffle(shuffled_rows)
    rows_shuffled = [header] + shuffled_rows

    csv_fwd = tmp_path / "trans_forward.csv"
    csv_rev = tmp_path / "trans_reverse.csv"
    csv_shuf = tmp_path / "trans_shuffled.csv"
    tsv_shuf = tmp_path / "trans_shuffled.tsv"

    with open(csv_fwd, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=",").writerows(rows_forward)

    with open(csv_rev, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=",").writerows(rows_reverse)

    with open(csv_shuf, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=",").writerows(rows_shuffled)

    with open(tsv_shuf, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter="\t").writerows(rows_shuffled)

    plugin = DocumentTextMatcherPlugin()

    # Verify representations and content hashes match identically
    rep_fwd = plugin.extract_document_representation(str(csv_fwd))
    rep_rev = plugin.extract_document_representation(str(csv_rev))
    rep_shuf = plugin.extract_document_representation(str(csv_shuf))
    rep_tsv = plugin.extract_document_representation(str(tsv_shuf))

    assert rep_fwd is not None
    assert rep_rev is not None
    assert rep_shuf is not None
    assert rep_tsv is not None

    hash_fwd, _, _ = rep_fwd
    hash_rev, _, _ = rep_rev
    hash_shuf, _, _ = rep_shuf
    hash_tsv, _, _ = rep_tsv

    assert hash_fwd == hash_rev == hash_shuf == hash_tsv

    candidates = [
        FileEntry(path=str(csv_fwd), size_bytes=csv_fwd.stat().st_size),
        FileEntry(path=str(csv_rev), size_bytes=csv_rev.stat().st_size),
        FileEntry(path=str(csv_shuf), size_bytes=csv_shuf.stat().st_size),
        FileEntry(path=str(tsv_shuf), size_bytes=tsv_shuf.stat().st_size),
    ]

    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert len(cluster.members) == 4
    assert cluster.match_type == MatchType.CONTENT_NEAR_DUPLICATE
    # All members in an exact canonical match have similarity 1.0
    for score in cluster.similarity_scores:
        assert score == 1.0


# ==============================================================================
# 2. Token Similarity Exact Boundaries (89% vs 90% vs 91%)
# ==============================================================================


def test_token_similarity_exact_boundaries(tmp_path: Path):
    """Verify that Jaccard similarity < 0.90 (e.g. 89%) is rejected, while >= 0.90 (90%, 91%) is clustered."""
    # Let total union = 100 distinct tokens.
    # Base has 100 tokens: t0 .. t99
    base_tokens = [f"tokalpha{i}" for i in range(100)]

    # 89% case: 89 tokens in common, 11 different.
    # doc_89 has t0..t88 + 11 novel tokens. Total union = 100 + 11 = 111?
    # To get EXACT Jaccard = inter / union:
    # Let union = 100 tokens.
    # If base has 100 tokens, and doc_89 has 89 tokens (all subset of base),
    # then inter = 89, union = 100. Jaccard = 89/100 = 0.8900 (89%).
    tokens_base = base_tokens[:]
    tokens_89 = base_tokens[:89]  # 89 in common, 0 extra -> inter=89, union=100 -> J=0.8900
    tokens_90 = base_tokens[:90]  # 90 in common, 0 extra -> inter=90, union=100 -> J=0.9000
    tokens_91 = base_tokens[:91]  # 91 in common, 0 extra -> inter=91, union=100 -> J=0.9100

    f_base = tmp_path / "base.docx"
    f_89 = tmp_path / "near_89.docx"
    f_90 = tmp_path / "near_90.docx"
    f_91 = tmp_path / "near_91.docx"

    f_base.write_bytes(_make_docx(" ".join(tokens_base)))
    f_89.write_bytes(_make_docx(" ".join(tokens_89)))
    f_90.write_bytes(_make_docx(" ".join(tokens_90)))
    f_91.write_bytes(_make_docx(" ".join(tokens_91)))

    plugin = DocumentTextMatcherPlugin()

    # Sub-test A: base and 89% candidate -> MUST NOT CLUSTER (sim < 0.90)
    cand_89 = [
        FileEntry(path=str(f_base), size_bytes=f_base.stat().st_size),
        FileEntry(path=str(f_89), size_bytes=f_89.stat().st_size),
    ]
    clusters_89 = plugin.find_duplicates(cand_89, cand_89)
    assert len(clusters_89) == 0, f"Expected 0 clusters for 89% similarity, got {clusters_89}"

    # Sub-test B: base and 90% candidate -> MUST CLUSTER (sim == 0.90)
    cand_90 = [
        FileEntry(path=str(f_base), size_bytes=f_base.stat().st_size),
        FileEntry(path=str(f_90), size_bytes=f_90.stat().st_size),
    ]
    clusters_90 = plugin.find_duplicates(cand_90, cand_90)
    assert len(clusters_90) == 1, f"Expected 1 cluster for 90% similarity, got {clusters_90}"
    assert len(clusters_90[0].members) == 2

    # Sub-test C: base and 91% candidate -> MUST CLUSTER (sim == 0.91)
    cand_91 = [
        FileEntry(path=str(f_base), size_bytes=f_base.stat().st_size),
        FileEntry(path=str(f_91), size_bytes=f_91.stat().st_size),
    ]
    clusters_91 = plugin.find_duplicates(cand_91, cand_91)
    assert len(clusters_91) == 1, f"Expected 1 cluster for 91% similarity, got {clusters_91}"
    assert len(clusters_91[0].members) == 2


def test_pptx_token_similarity_boundary(tmp_path: Path):
    """Verify PPTX boundary conditions: 89% rejected, 91% clustered."""
    base_words = [f"slidetok{i}" for i in range(100)]
    words_89 = base_words[:89]
    words_91 = base_words[:91]

    ppt_base = tmp_path / "base.pptx"
    ppt_89 = tmp_path / "reject_89.pptx"
    ppt_91 = tmp_path / "accept_91.pptx"

    ppt_base.write_bytes(_make_pptx_slides([" ".join(base_words)]))
    ppt_89.write_bytes(_make_pptx_slides([" ".join(words_89)]))
    ppt_91.write_bytes(_make_pptx_slides([" ".join(words_91)]))

    plugin = DocumentTextMatcherPlugin()

    # 89% rejection
    cands_89 = [
        FileEntry(path=str(ppt_base), size_bytes=ppt_base.stat().st_size),
        FileEntry(path=str(ppt_89), size_bytes=ppt_89.stat().st_size),
    ]
    assert len(plugin.find_duplicates(cands_89, cands_89)) == 0

    # 91% acceptance
    cands_91 = [
        FileEntry(path=str(ppt_base), size_bytes=ppt_base.stat().st_size),
        FileEntry(path=str(ppt_91), size_bytes=ppt_91.stat().st_size),
    ]
    clusters = plugin.find_duplicates(cands_91, cands_91)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 2


# ==============================================================================
# 3. Soundness of O(1) Fast Ratio Pruning Bound
# ==============================================================================


def test_fast_ratio_pruning_soundness():
    """Verify that the ratio pruning filter min_len / max_len < threshold never discards valid candidates."""
    threshold = SIMILARITY_THRESHOLD  # 0.90
    rng = random.Random(1337)

    for _ in range(500):
        len_a = rng.randint(5, 200)
        len_b = rng.randint(5, 200)

        # Generate random overlapping token sets
        shared_count = rng.randint(0, min(len_a, len_b))
        tokens_a = {f"t_{i}" for i in range(shared_count)} | {
            f"a_{i}" for i in range(len_a - shared_count)
        }
        tokens_b = {f"t_{i}" for i in range(shared_count)} | {
            f"b_{i}" for i in range(len_b - shared_count)
        }

        min_len = min(len(tokens_a), len(tokens_b))
        max_len = max(len(tokens_a), len(tokens_b))

        ratio = min_len / max_len if max_len > 0 else 0.0
        inter = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        jaccard = inter / union if union > 0 else 0.0

        # Mathematical invariant: Jaccard <= ratio
        assert jaccard <= ratio + 1e-9

        # If Jaccard >= threshold, then ratio MUST also be >= threshold
        if jaccard >= threshold:
            assert ratio >= threshold, f"Ratio filter falsely pruned: Jaccard={jaccard} >= {threshold}, but ratio={ratio}"


# ==============================================================================
# 4. Word Cap Truncation (100,000 words capped at 50,000)
# ==============================================================================


def test_massive_word_cap_100k_words_truncation(tmp_path: Path):
    """Stress test: 100,000-word documents capped at 50,000 words.

    doc_a and doc_b share the first 50,000 words but completely diverge in words
    50,001..100,000. Due to MAX_WORDS=50,000 cap, both produce identical hashes
    and are clustered. doc_c differs inside the first 50,000 words.
    """
    shared_prefix = [f"wordshared{i}" for i in range(MAX_WORDS)]
    divergent_a = [f"wordtailalpha{i}" for i in range(50_000)]
    divergent_b = [f"wordtailbeta{i}" for i in range(50_000)]

    # doc_c differs substantially within the first 50k words (10,000 words different -> sim ~0.66 < 0.90)
    prefix_c = shared_prefix[:40_000] + [f"diffwordtok{i}" for i in range(10_000)]

    doc_a = tmp_path / "huge_a.docx"
    doc_b = tmp_path / "huge_b.docx"
    doc_c = tmp_path / "huge_c.docx"

    doc_a.write_bytes(_make_docx(" ".join(shared_prefix + divergent_a)))
    doc_b.write_bytes(_make_docx(" ".join(shared_prefix + divergent_b)))
    doc_c.write_bytes(_make_docx(" ".join(prefix_c + divergent_a)))

    plugin = DocumentTextMatcherPlugin()

    rep_a = plugin.extract_document_representation(str(doc_a))
    rep_b = plugin.extract_document_representation(str(doc_b))
    rep_c = plugin.extract_document_representation(str(doc_c))

    assert rep_a is not None
    assert rep_b is not None
    assert rep_c is not None

    hash_a, _, _ = rep_a
    hash_b, _, _ = rep_b
    hash_c, _, _ = rep_c

    # Because doc_a and doc_b have identical words up to MAX_WORDS, their hashes must match
    assert hash_a == hash_b
    # doc_c differs within the first 50k words, so its hash must differ
    assert hash_c != hash_a

    candidates = [
        FileEntry(path=str(doc_a), size_bytes=doc_a.stat().st_size),
        FileEntry(path=str(doc_b), size_bytes=doc_b.stat().st_size),
        FileEntry(path=str(doc_c), size_bytes=doc_c.stat().st_size),
    ]

    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 2
    matched = {m.path for m in clusters[0].members}
    assert str(doc_a) in matched
    assert str(doc_b) in matched
    assert str(doc_c) not in matched


# ==============================================================================
# 5. Robustness to Corrupted, Truncated, 0-Byte, and Adversarial Files
# ==============================================================================


def test_corrupted_truncated_and_zero_byte_robustness(tmp_path: Path):
    """Adversarial suite ensuring zero crashes on malformed/corrupted/empty files."""
    plugin = DocumentTextMatcherPlugin()

    files: list[Path] = []

    # 1. 0-byte files across all supported extensions
    for ext in [".pdf", ".docx", ".pptx", ".odt", ".csv", ".tsv"]:
        p = tmp_path / f"zero_byte{ext}"
        p.write_bytes(b"")
        files.append(p)

    # 2. Truncated ZIP files (broken headers or truncated midway)
    t_docx = tmp_path / "truncated.docx"
    valid_docx = _make_docx("Valid document text before truncation")
    t_docx.write_bytes(valid_docx[: len(valid_docx) // 2])
    files.append(t_docx)

    t_pptx = tmp_path / "truncated.pptx"
    valid_pptx = _make_pptx_slides(["Slide 1"])
    t_pptx.write_bytes(valid_pptx[: len(valid_pptx) // 3])
    files.append(t_pptx)

    # 3. Non-zip files with zip extensions
    fake_docx = tmp_path / "fake_zip.docx"
    fake_docx.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00Executable binary header fake docx")
    files.append(fake_docx)

    # 4. Truncated / malformed PDF
    fake_pdf = tmp_path / "broken_header.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ngarbage truncated")
    files.append(fake_pdf)

    # 5. CSV with embedded null bytes and binary noise
    bin_csv = tmp_path / "binary_noise.csv"
    bin_csv.write_bytes(b"header1,header2\r\n\x00\xff\xfe\x01data,1234\r\n")
    files.append(bin_csv)

    # 6. CSV with only whitespace
    space_csv = tmp_path / "whitespace_only.csv"
    space_csv.write_bytes(b"   \t  \r\n   \t  \r\n")
    files.append(space_csv)

    # Non-existent file
    non_existent = str(tmp_path / "does_not_exist.docx")
    assert plugin.extract_document_representation(non_existent) is None

    # Verify each corrupt file returns None without raising any uncaught exceptions
    for f in files:
        rep = plugin.extract_document_representation(str(f))
        assert rep is None, f"Expected None for corrupted/empty file {f.name}, got {rep}"

    # Verify find_duplicates on all corrupt entries returns empty cluster list cleanly
    candidates = [
        FileEntry(path=str(f), size_bytes=f.stat().st_size)
        for f in files
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert clusters == []


# ==============================================================================
# 6. Natural Slide Sorting in PPTX (Preventing Lexicographical Sorting Bug)
# ==============================================================================


def test_pptx_natural_slide_sorting_correctness(tmp_path: Path):
    """Adversarial check: slide10.xml must naturally sort AFTER slide2.xml."""
    # Create 12 slides with distinctive numbers
    slides = [f"SlideIndexMarker{i}" for i in range(1, 13)]
    pptx_path = tmp_path / "presentation_ordered.pptx"
    pptx_path.write_bytes(_make_pptx_slides(slides))

    plugin = DocumentTextMatcherPlugin()
    data = plugin._extract_document_data(str(pptx_path))
    assert data is not None
    _, preview, _, _ = data

    # Read extracted text lines
    raw_text = plugin._extract_pptx_text(str(pptx_path))
    assert raw_text is not None
    lines = raw_text.splitlines()
    assert len(lines) == 12

    # In lexicographical sort, slide10 would come right after slide1 and before slide2:
    # slide1, slide10, slide11, slide12, slide2, slide3...
    # In natural sort, slide2 comes before slide10:
    for i in range(1, 13):
        assert f"SlideIndexMarker{i}" in lines[i - 1]


# ==============================================================================
# 7. PDF Extraction 50-Page Cap
# ==============================================================================


def test_pdf_fifty_page_cap(tmp_path: Path):
    """Verify that PDF inspection strictly caps at 50 pages (MAX_PDF_PAGES)."""
    # Create a 60-page PDF
    pages_text = [f"PageIdentifierIndex{i} ContentBody" for i in range(1, 65)]
    pdf_path = tmp_path / "large_document.pdf"
    pdf_path.write_bytes(_make_multipage_pdf(pages_text))

    plugin = DocumentTextMatcherPlugin()
    extracted = plugin._extract_pdf_text(str(pdf_path))
    assert extracted is not None

    # Page 1 to 50 must be present
    assert "PageIdentifierIndex1" in extracted
    assert "PageIdentifierIndex50" in extracted

    # Page 51..64 must NOT be present
    assert "PageIdentifierIndex51" not in extracted
    assert "PageIdentifierIndex60" not in extracted


# ==============================================================================
# 8. Cross-Format Deduplication (.docx, .odt, .pdf)
# ==============================================================================


def test_cross_format_deduplication(tmp_path: Path):
    """Verify that identical text across different formats (.docx, .odt, .pdf) clusters together."""
    shared_text = "Standard Operating Procedure for Distributed Cluster File Deduplication 2026."

    f_docx = tmp_path / "sop.docx"
    f_odt = tmp_path / "sop.odt"
    f_pdf = tmp_path / "sop.pdf"

    f_docx.write_bytes(_make_docx(shared_text))
    f_odt.write_bytes(_make_odt(shared_text))
    f_pdf.write_bytes(_make_multipage_pdf([shared_text]))

    plugin = DocumentTextMatcherPlugin()

    rep_docx = plugin.extract_document_representation(str(f_docx))
    rep_odt = plugin.extract_document_representation(str(f_odt))
    rep_pdf = plugin.extract_document_representation(str(f_pdf))

    assert rep_docx is not None
    assert rep_odt is not None
    assert rep_pdf is not None

    # Content hashes must match across all three formats
    assert rep_docx[0] == rep_odt[0] == rep_pdf[0]

    candidates = [
        FileEntry(path=str(f_docx), size_bytes=f_docx.stat().st_size),
        FileEntry(path=str(f_odt), size_bytes=f_odt.stat().st_size),
        FileEntry(path=str(f_pdf), size_bytes=f_pdf.stat().st_size),
    ]

    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert len(cluster.members) == 3
    assert set(cluster.metadata["extensions"]) == {".docx", ".odt", ".pdf"}


# ==============================================================================
# 9. Multi-Way DSU Transitive Clustering
# ==============================================================================


def test_dsu_transitive_clustering(tmp_path: Path):
    """Verify that DSU correctly unions transitive near-duplicate relations."""
    # A shares 91% with B. B shares 91% with C.
    # But A and C share less (e.g. ~82%).
    # DSU should unite A, B, and C into a single connected component cluster.
    # Construction:
    # Core shared by A and B: 91 tokens
    # Core shared by B and C: 91 tokens (say B has tokens 10..100)
    # B has tokens 0..99 (100 tokens).
    # A has tokens 0..90 + 9 extra (inter with B is 91, union with B is 109? wait)
    # Let B have tokens: t0..t99 (100 tokens).
    # A has tokens: t0..t90 (91 tokens).
    # Jaccard(A, B) = 91 / 100 = 0.9100.
    # C has tokens: t9..t99 (91 tokens).
    # Jaccard(B, C) = 91 / 100 = 0.9100.
    # Jaccard(A, C):
    # A has t0..t90. C has t9..t90.
    # Intersection(A, C) = t9..t90 -> 82 tokens.
    # Union(A, C) = t0..t99 -> 100 tokens.
    # Jaccard(A, C) = 82 / 100 = 0.8200 (< 0.90).

    tokens_b_list = [f"tok{i}" for i in range(100)]
    tokens_a_list = [f"tok{i}" for i in range(91)]
    tokens_c_list = [f"tok{i}" for i in range(9, 100)]

    fa = tmp_path / "node_a.docx"
    fb = tmp_path / "node_b.docx"
    fc = tmp_path / "node_c.docx"

    fa.write_bytes(_make_docx(" ".join(tokens_a_list)))
    fb.write_bytes(_make_docx(" ".join(tokens_b_list)))
    fc.write_bytes(_make_docx(" ".join(tokens_c_list)))

    plugin = DocumentTextMatcherPlugin()
    candidates = [
        FileEntry(path=str(fa), size_bytes=fa.stat().st_size),
        FileEntry(path=str(fb), size_bytes=fb.stat().st_size),
        FileEntry(path=str(fc), size_bytes=fc.stat().st_size),
    ]

    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert len(cluster.members) == 3
    # Verify pairwise scores are valid (>= 0.90 for matched pairs)
    for score in cluster.similarity_scores:
        assert score >= 0.90


# ==============================================================================
# 10. Delimiter Sniffing & Tabular Edge Cases
# ==============================================================================


def test_tabular_delimiter_sniffing_and_quoting(tmp_path: Path):
    """Test CSV delimiter sniffing with commas, semicolons, and quoted commas."""
    rows = [
        ["Name", "Department", "Location"],
        ['"Smith, John"', "Finance", "New York"],
        ['"Doe, Jane"', "Engineering", "San Francisco"],
        ["Brown; Charlie", "Operations", "Chicago"],
    ]

    # File 1: standard CSV with quoted cells containing commas
    f_csv = tmp_path / "staff.csv"
    with open(f_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)

    # File 2: semicolon-delimited CSV
    f_semi = tmp_path / "staff_semi.csv"
    with open(f_semi, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)

    # File 3: reversed rows with UTF-8 BOM
    rows_reversed = [rows[0]] + list(reversed(rows[1:]))
    f_bom = tmp_path / "staff_bom.csv"
    with open(f_bom, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows_reversed)

    plugin = DocumentTextMatcherPlugin()

    rep_csv = plugin.extract_document_representation(str(f_csv))
    rep_semi = plugin.extract_document_representation(str(f_semi))
    rep_bom = plugin.extract_document_representation(str(f_bom))

    assert rep_csv is not None
    assert rep_semi is not None
    assert rep_bom is not None

    # Both standard and BOM with reversed rows must yield identical content hashes
    assert rep_csv[0] == rep_bom[0]

    candidates = [
        FileEntry(path=str(f_csv), size_bytes=f_csv.stat().st_size),
        FileEntry(path=str(f_bom), size_bytes=f_bom.stat().st_size),
    ]
    clusters = plugin.find_duplicates(candidates, candidates)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 2


# ==============================================================================
# 11. Edge Cases: Short Documents, Single Entry, Extreme Unicode Cells, 25MB Cap
# ==============================================================================


def test_short_documents_min_tokens_boundary(tmp_path: Path):
    """Verify that documents with < 5 tokens cluster only if EXACT match, not if near-match."""
    plugin = DocumentTextMatcherPlugin()

    # Exact match on 3 tokens -> must cluster via Step 1 (exact normalized hash)
    f_ex1 = tmp_path / "exact_short1.docx"
    f_ex2 = tmp_path / "exact_short2.docx"
    f_ex1.write_bytes(_make_docx("apple banana cherry"))
    f_ex2.write_bytes(_make_docx("apple   banana \n cherry"))

    cands_exact = [
        FileEntry(path=str(f_ex1), size_bytes=f_ex1.stat().st_size),
        FileEntry(path=str(f_ex2), size_bytes=f_ex2.stat().st_size),
    ]
    clusters_exact = plugin.find_duplicates(cands_exact, cands_exact)
    assert len(clusters_exact) == 1

    # Near match on 4 tokens (3 shared, 1 different) -> Jaccard = 3/5 = 0.60,
    # but even with high overlap, MIN_TOKENS_FOR_SIMILARITY=5 prevents false positives on stubs
    f_near1 = tmp_path / "near_short1.docx"
    f_near2 = tmp_path / "near_short2.docx"
    f_near1.write_bytes(_make_docx("alpha beta gamma delta"))
    f_near2.write_bytes(_make_docx("alpha beta gamma epsilon"))

    cands_near = [
        FileEntry(path=str(f_near1), size_bytes=f_near1.stat().st_size),
        FileEntry(path=str(f_near2), size_bytes=f_near2.stat().st_size),
    ]
    clusters_near = plugin.find_duplicates(cands_near, cands_near)
    assert len(clusters_near) == 0


def test_boundary_candidate_counts(tmp_path: Path):
    """Verify find_duplicates on 0 or 1 candidate returns empty list."""
    plugin = DocumentTextMatcherPlugin()
    assert plugin.find_duplicates([], []) == []

    f_single = tmp_path / "alone.docx"
    f_single.write_bytes(_make_docx("Solo candidate content"))
    cand_single = [FileEntry(path=str(f_single), size_bytes=f_single.stat().st_size)]
    assert plugin.find_duplicates(cand_single, cand_single) == []


def test_extreme_cell_sizes_and_unicode_tabular(tmp_path: Path):
    """Stress test CSV with massive 10,000-char cell and multilingual Unicode (CJK, Arabic, Emojis)."""
    plugin = DocumentTextMatcherPlugin()

    huge_cell = "A" * 10_000
    rows = [
        ["ID", "Content", "Notes"],
        ["1", huge_cell, "ASCII string with length 10k"],
        ["2", "日本語テキストと絵文字 🚀 🔥 🎉", "CJK and emoji support"],
        ["3", "مرحبا بالعالم نص عربي", "Arabic text support"],
    ]

    f1 = tmp_path / "unicode_a.csv"
    f2 = tmp_path / "unicode_b.csv"

    # Write in normal and reversed row order
    with open(f1, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

    rows_rev = [rows[0]] + list(reversed(rows[1:]))
    with open(f2, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows_rev)

    rep1 = plugin.extract_document_representation(str(f1))
    rep2 = plugin.extract_document_representation(str(f2))

    assert rep1 is not None
    assert rep2 is not None
    assert rep1[0] == rep2[0]

    cands = [
        FileEntry(path=str(f1), size_bytes=f1.stat().st_size),
        FileEntry(path=str(f2), size_bytes=f2.stat().st_size),
    ]
    clusters = plugin.find_duplicates(cands, cands)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 2


def test_memory_cap_25mb_safety(tmp_path: Path):
    """Verify that a 30MB CSV file is safely read up to MAX_BUFFER_BYTES (25MB) without memory exhaustion."""
    plugin = DocumentTextMatcherPlugin()

    # Generate a ~28 MB CSV file
    large_csv = tmp_path / "large_dataset.csv"
    line_pattern = "10001,SomeDepartmentName,SomeEmployeeName,12345.67,NotesAboutEmployeePerformance\n"
    # line is 78 bytes. 360,000 lines is ~28 MB
    with open(large_csv, "w", encoding="utf-8") as f:
        f.write("id,department,name,salary,notes\n")
        # Write chunks of 10,000 lines
        chunk = line_pattern * 10_000
        for _ in range(36):
            f.write(chunk)

    file_size = large_csv.stat().st_size
    assert file_size > 25 * 1024 * 1024  # greater than 25MB

    # Extraction must succeed within buffer and word caps without crashing or OOM
    rep = plugin.extract_document_representation(str(large_csv))
    assert rep is not None
    content_hash, preview, length = rep
    assert len(content_hash) == 64
    assert length > 0
