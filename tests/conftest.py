"""
Clairvoy Test Fixtures & Shared Configuration
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def temp_workspace():
    """Provides an isolated temporary directory for file system tests."""
    temp_dir = tempfile.mkdtemp(prefix="clairvoy_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_dataset(temp_workspace):
    """Creates a sample file directory with exact duplicates and unique files."""
    data_dir = temp_workspace / "data"
    data_dir.mkdir()

    # Original files
    content_a = b"Exact duplicate content payload 123456789" * 100
    content_b = b"Different unique content payload 987654321" * 100

    file1 = data_dir / "document_original.txt"
    file2 = data_dir / "document_copy (1).txt"
    file3 = data_dir / "unique_report.txt"

    file1.write_bytes(content_a)
    file2.write_bytes(content_a)
    file3.write_bytes(content_b)

    # Subfolder with nested duplicate
    sub = data_dir / "nested_folder"
    sub.mkdir()
    file4 = sub / "another_copy.txt"
    file4.write_bytes(content_a)

    return {
        "root": data_dir,
        "files": [file1, file2, file3, file4],
        "duplicate_count": 3,
    }


@pytest.fixture
def sample_images(temp_workspace):
    """Generates synthetic test images (identical and different colors)."""
    img_dir = temp_workspace / "images"
    img_dir.mkdir()

    # Red image (original)
    img_red1 = Image.new("RGB", (300, 300), color=(255, 0, 0))
    p1 = img_dir / "photo_red_original.jpg"
    img_red1.save(p1)

    # Identical Red image with copy name
    p2 = img_dir / "photo_red_copy (1).jpg"
    img_red1.save(p2)

    # Blue image (completely distinct)
    img_blue = Image.new("RGB", (300, 300), color=(0, 0, 255))
    p3 = img_dir / "photo_blue_distinct.jpg"
    img_blue.save(p3)

    return {
        "root": img_dir,
        "red1": p1,
        "red2": p2,
        "blue": p3,
    }


@pytest.fixture
def multi_root_dataset(temp_workspace):
    """Creates two distinct root folders with cross-folder duplicate files."""
    root_a = temp_workspace / "remote_drive_a"
    root_b = temp_workspace / "remote_drive_b"
    root_a.mkdir()
    root_b.mkdir()

    shared_content = b"Cross-remote duplicate file payload 999888777" * 50
    unique_a = b"Unique to drive A"
    unique_b = b"Unique to drive B"

    # Drive A files
    file_a1 = root_a / "project_specs.pdf"
    file_a2 = root_a / "notes.txt"
    file_a1.write_bytes(shared_content)
    file_a2.write_bytes(unique_a)

    # Drive B files (contains copy of project_specs with different filename)
    file_b1 = root_b / "project_specs (backup).pdf"
    file_b2 = root_b / "summary.txt"
    file_b1.write_bytes(shared_content)
    file_b2.write_bytes(unique_b)

    return {
        "root_a": root_a,
        "root_b": root_b,
        "shared_file_a": file_a1,
        "shared_file_b": file_b1,
    }


@pytest.fixture(autouse=True)
def isolate_global_runs_history(tmp_path, monkeypatch):
    """Prevents tests from modifying ~/.clairvoy/runs.json in the user's real home directory."""
    from clairvoy.core.run_manager import RunManager

    orig_init = RunManager.__init__
    test_runs_file = tmp_path / "pytest_isolated_runs.json"

    def mock_init(self, history_file=None):
        orig_init(self, history_file=history_file or test_runs_file)

    monkeypatch.setattr(RunManager, "__init__", mock_init)

