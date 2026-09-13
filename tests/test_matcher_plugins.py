"""
Unit tests for Clairvoy Matcher Plugins:
- ExactHashMatcherPlugin
- ArchiveInspectorMatcherPlugin
"""

import tarfile
import zipfile
from pathlib import Path

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import PluginRegistry
from clairvoy.plugins.archive_inspector import ArchiveInspectorMatcherPlugin
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin


def test_exact_hash_matcher_properties():
    matcher = ExactHashMatcherPlugin()
    assert matcher.plugin_id == "exact_hash"
    assert matcher.display_name == "Exact Hash Matcher (QuickHash + SHA-256)"
    assert matcher.version == "0.1.0"
    assert matcher.author == "Clairvoy Team"
    assert "QuickHash" in matcher.description
    assert matcher.match_type == MatchType.EXACT_HASH
    assert matcher.priority_order == 10
    is_avail, reason = matcher.is_available()
    assert is_avail is True
    assert "hashlib" in reason


def test_exact_hash_matcher(temp_workspace: Path):
    f1 = temp_workspace / "file1.txt"
    f2 = temp_workspace / "file2.txt"
    f3 = temp_workspace / "unique.txt"
    f1.write_text("duplicate content 123456789")
    f2.write_text("duplicate content 123456789")
    f3.write_text("unique content 987654321")

    entries = [
        FileEntry(path=str(f1), size_bytes=f1.stat().st_size),
        FileEntry(path=str(f2), size_bytes=f2.stat().st_size),
        FileEntry(path=str(f3), size_bytes=f3.stat().st_size),
    ]

    matcher = ExactHashMatcherPlugin()
    filtered = matcher.filter_supported(entries)
    assert len(filtered) == 3

    clusters = matcher.find_duplicates(entries, entries, context={})

    assert len(clusters) == 1
    assert clusters[0].cluster_id == 1
    assert clusters[0].match_type == MatchType.EXACT_HASH
    assert len(clusters[0].members) == 2
    paths = {m.path for m in clusters[0].members}
    assert str(f1) in paths and str(f2) in paths
    assert str(f3) not in paths
    assert clusters[0].similarity_scores == [1.0, 1.0]
    assert "sha256" in clusters[0].metadata
    assert clusters[0].metadata["size_bytes"] == f1.stat().st_size


def test_exact_hash_matcher_multiple_clusters(temp_workspace: Path):
    a1 = temp_workspace / "a1.bin"
    a2 = temp_workspace / "a2.bin"
    b1 = temp_workspace / "b1.bin"
    b2 = temp_workspace / "b2.bin"
    u = temp_workspace / "u.bin"

    a1.write_bytes(b"GROUP_A_PAYLOAD" * 20)
    a2.write_bytes(b"GROUP_A_PAYLOAD" * 20)
    b1.write_bytes(b"GROUP_B_PAYLOAD_DIFF" * 15)
    b2.write_bytes(b"GROUP_B_PAYLOAD_DIFF" * 15)
    u.write_bytes(b"UNIQUE_PAYLOAD_DATA" * 10)

    entries = [
        FileEntry(path=str(a1), size_bytes=a1.stat().st_size),
        FileEntry(path=str(a2), size_bytes=a2.stat().st_size),
        FileEntry(path=str(b1), size_bytes=b1.stat().st_size),
        FileEntry(path=str(b2), size_bytes=b2.stat().st_size),
        FileEntry(path=str(u), size_bytes=u.stat().st_size),
    ]

    matcher = ExactHashMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={"start_cluster_id": 10})

    assert len(clusters) == 2
    cluster_ids = {c.cluster_id for c in clusters}
    assert cluster_ids == {10, 11}


def test_exact_hash_matcher_quick_hash_collision(temp_workspace: Path):
    # Two files share the first 128KB header, but differ in trailing bytes
    header = b"H" * (128 * 1024)
    f1 = temp_workspace / "collision_1.bin"
    f2 = temp_workspace / "collision_2.bin"
    f1.write_bytes(header + b"TAIL_1_DIFFERENCE")
    f2.write_bytes(header + b"TAIL_2_DIFFERENCE")

    entries = [
        FileEntry(path=str(f1), size_bytes=f1.stat().st_size),
        FileEntry(path=str(f2), size_bytes=f2.stat().st_size),
    ]

    matcher = ExactHashMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={})

    # Should not cluster because full sha256 differs
    assert len(clusters) == 0
    assert entries[0].quick_hash == entries[1].quick_hash
    assert entries[0].full_sha256 != entries[1].full_sha256


def test_exact_hash_matcher_empty_files(temp_workspace: Path):
    e1 = temp_workspace / "empty1.txt"
    e2 = temp_workspace / "empty2.txt"
    e1.write_bytes(b"")
    e2.write_bytes(b"")

    entries = [
        FileEntry(path=str(e1), size_bytes=0),
        FileEntry(path=str(e2), size_bytes=0),
    ]

    matcher = ExactHashMatcherPlugin()
    assert matcher.filter_supported(entries) == []

    clusters = matcher.find_duplicates(entries, entries, context={})
    assert len(clusters) == 0


def test_exact_hash_matcher_unreadable_file(temp_workspace: Path):
    f1 = temp_workspace / "missing1.txt"
    f2 = temp_workspace / "missing2.txt"
    # Neither file actually created on disk

    entries = [
        FileEntry(path=str(f1), size_bytes=100),
        FileEntry(path=str(f2), size_bytes=100),
    ]

    matcher = ExactHashMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={})
    assert clusters == []


def test_archive_inspector_properties():
    matcher = ArchiveInspectorMatcherPlugin()
    assert matcher.plugin_id == "archive_inspector"
    assert matcher.display_name == "Archive Inspector Matcher (ZIP/TAR Inspection)"
    assert matcher.version == "0.1.0"
    assert matcher.author == "Clairvoy Team"
    assert "ZIP" in matcher.description
    assert matcher.match_type == MatchType.EXACT_HASH
    assert matcher.priority_order == 40
    is_avail, reason = matcher.is_available()
    assert is_avail is True
    assert "zipfile" in reason


def test_archive_inspector_zip(temp_workspace: Path):
    doc = temp_workspace / "invoice.pdf"
    doc_content = b"PDF invoice content for client XYZ 12345"
    doc.write_bytes(doc_content)

    zip_path = temp_workspace / "backup.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("invoices/invoice.pdf", doc_content)

    entries = [
        FileEntry(path=str(doc), size_bytes=len(doc_content)),
        FileEntry(path=str(zip_path), size_bytes=zip_path.stat().st_size),
    ]

    matcher = ArchiveInspectorMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={})

    assert len(clusters) == 1
    assert "invoice.pdf" in clusters[0].members[0].path
    assert clusters[0].members[0].path == str(doc)
    assert clusters[0].members[1].path == f"{zip_path}::invoices/invoice.pdf"
    assert clusters[0].similarity_scores == [1.0, 1.0]
    assert clusters[0].metadata["archive"] == str(zip_path)
    assert clusters[0].metadata["member"] == "invoices/invoice.pdf"
    assert "crc32" in clusters[0].metadata


def test_archive_inspector_different_content(temp_workspace: Path):
    # Same size, different content
    doc = temp_workspace / "file_a.txt"
    doc.write_bytes(b"A" * 50)

    zip_path = temp_workspace / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("file_b.txt", b"B" * 50)

    entries = [
        FileEntry(path=str(doc), size_bytes=50),
        FileEntry(path=str(zip_path), size_bytes=zip_path.stat().st_size),
    ]

    matcher = ArchiveInspectorMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={})
    assert len(clusters) == 0


def test_archive_inspector_corrupt_zip(temp_workspace: Path):
    bad_zip = temp_workspace / "corrupted.zip"
    bad_zip.write_bytes(b"NOT A VALID ZIP FILE HEADER JUNK BYTES")

    doc = temp_workspace / "valid.txt"
    doc.write_bytes(b"hello world")

    entries = [
        FileEntry(path=str(doc), size_bytes=doc.stat().st_size),
        FileEntry(path=str(bad_zip), size_bytes=bad_zip.stat().st_size),
    ]

    matcher = ArchiveInspectorMatcherPlugin()
    # Must handle gracefully without raising BadZipFile
    clusters = matcher.find_duplicates(entries, entries, context={})
    assert clusters == []


def test_archive_inspector_tar(temp_workspace: Path):
    doc = temp_workspace / "data.csv"
    doc_content = b"id,name,value\n1,alice,100\n2,bob,200\n"
    doc.write_bytes(doc_content)

    tar_path = temp_workspace / "data.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        tarinfo = tarfile.TarInfo(name="exports/data.csv")
        tarinfo.size = len(doc_content)
        import io
        tf.addfile(tarinfo, io.BytesIO(doc_content))

    entries = [
        FileEntry(path=str(doc), size_bytes=len(doc_content)),
        FileEntry(path=str(tar_path), size_bytes=tar_path.stat().st_size),
    ]

    matcher = ArchiveInspectorMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={})

    assert len(clusters) == 1
    assert "data.csv" in clusters[0].members[0].path
    assert clusters[0].members[1].path == f"{tar_path}::exports/data.csv"


def test_archive_inspector_skips_dirs_and_empty(temp_workspace: Path):
    zip_path = temp_workspace / "empty_and_dirs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        # Directory member
        zinfo_dir = zipfile.ZipInfo("somedir/")
        zf.writestr(zinfo_dir, "")
        # 0-byte file member
        zf.writestr("empty_inside.txt", "")

    doc = temp_workspace / "empty_disk.txt"
    doc.write_bytes(b"")

    entries = [
        FileEntry(path=str(doc), size_bytes=0),
        FileEntry(path=str(zip_path), size_bytes=zip_path.stat().st_size),
    ]

    matcher = ArchiveInspectorMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={})
    assert clusters == []


def test_matcher_plugins_registry_integration():
    registry = PluginRegistry()
    exact_hash = ExactHashMatcherPlugin()
    archive_inspector = ArchiveInspectorMatcherPlugin()

    registry.register(archive_inspector)
    registry.register(exact_hash)

    matchers = registry.get_matchers()
    assert len(matchers) == 2
    # Verify exact_hash (priority 10) runs before archive_inspector (priority 40)
    assert matchers[0].plugin_id == "exact_hash"
    assert matchers[0].priority_order == 10
    assert matchers[1].plugin_id == "archive_inspector"
    assert matchers[1].priority_order == 40
