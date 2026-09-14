"""Tests for ArchiveInspectorMatcherPlugin expansion (.jar, .apk, .rar)."""

import zipfile
from pathlib import Path

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.plugins.archive_inspector import ARCHIVE_SUFFIXES, ArchiveInspectorMatcherPlugin


def test_archive_suffixes_includes_jar_apk_rar():
    assert ".jar" in ARCHIVE_SUFFIXES
    assert ".apk" in ARCHIVE_SUFFIXES
    assert ".rar" in ARCHIVE_SUFFIXES


def test_archive_inspector_matches_member_in_jar(tmp_path: Path):
    jar_file = tmp_path / "app.jar"
    content = b"public class App { public static void main(String[] args) {} }"
    with zipfile.ZipFile(jar_file, "w") as zf:
        zf.writestr("App.class", content)

    on_disk_class = tmp_path / "App.class"
    on_disk_class.write_bytes(content)

    plugin = ArchiveInspectorMatcherPlugin()
    candidates = [FileEntry(path=str(on_disk_class), size_bytes=len(content))]
    all_files = candidates + [FileEntry(path=str(jar_file), size_bytes=jar_file.stat().st_size)]

    clusters = plugin.find_duplicates(candidates, all_files)
    assert len(clusters) == 1
    assert clusters[0].match_type == MatchType.EXACT_HASH
    assert clusters[0].metadata["archive"] == str(jar_file)
    assert clusters[0].metadata["member"] == "App.class"


def test_archive_inspector_matches_member_in_apk(tmp_path: Path):
    apk_file = tmp_path / "release.apk"
    content = b"manifest XML binary data"
    with zipfile.ZipFile(apk_file, "w") as zf:
        zf.writestr("AndroidManifest.xml", content)

    on_disk_manifest = tmp_path / "AndroidManifest.xml"
    on_disk_manifest.write_bytes(content)

    plugin = ArchiveInspectorMatcherPlugin()
    candidates = [FileEntry(path=str(on_disk_manifest), size_bytes=len(content))]
    all_files = candidates + [FileEntry(path=str(apk_file), size_bytes=apk_file.stat().st_size)]

    clusters = plugin.find_duplicates(candidates, all_files)
    assert len(clusters) == 1
    assert clusters[0].metadata["member"] == "AndroidManifest.xml"


def test_archive_inspector_handles_rar_gracefully(tmp_path: Path):
    rar_file = tmp_path / "sample.rar"
    rar_file.write_bytes(b"Rar!\x1a\x07\x00" + b"\x00" * 30)

    on_disk_doc = tmp_path / "doc.txt"
    on_disk_doc.write_bytes(b"Some text")

    plugin = ArchiveInspectorMatcherPlugin()
    candidates = [FileEntry(path=str(on_disk_doc), size_bytes=len(b"Some text"))]
    all_files = candidates + [FileEntry(path=str(rar_file), size_bytes=rar_file.stat().st_size)]

    # Does not crash on RAR without rarfile/unrar
    clusters = plugin.find_duplicates(candidates, all_files)
    assert isinstance(clusters, list)
