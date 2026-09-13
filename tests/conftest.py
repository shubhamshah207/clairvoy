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
