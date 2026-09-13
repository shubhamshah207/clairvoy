"""
Unit Tests for Image Classifier Engine
"""

import numpy as np
from PIL import Image

from clairvoy.core.models import ImageCategory
from clairvoy.engines.classifier_engine import ClassifierEngine


def test_classify_by_filename(temp_workspace):
    # Screenshot by filename
    p_sc = temp_workspace / "Screenshot_2023-11-20_0912.png"
    Image.new("RGB", (200, 200), color=(100, 100, 100)).save(p_sc)
    assert ClassifierEngine.classify_image(str(p_sc)) == ImageCategory.SCREENSHOT

    # Document by filename
    p_doc = temp_workspace / "tax_invoice_2023.jpg"
    Image.new("RGB", (200, 200), color=(255, 255, 255)).save(p_doc)
    assert ClassifierEngine.classify_image(str(p_doc)) == ImageCategory.DOCUMENT

    # Graphic by filename
    p_meme = temp_workspace / "funny_meme_cat.png"
    Image.new("RGB", (200, 200), color=(255, 0, 128)).save(p_meme)
    assert ClassifierEngine.classify_image(str(p_meme)) == ImageCategory.GRAPHIC


def test_classify_document_by_whiteness(temp_workspace):
    # A scanned page or receipt: predominantly white with black text lines
    p_receipt = temp_workspace / "paper_scan.jpg"
    img = Image.new("RGB", (300, 400), color=(250, 250, 250))
    # Draw some dark lines
    arr = np.array(img)
    arr[100:110, 50:250] = (20, 20, 20)
    arr[150:160, 50:250] = (20, 20, 20)
    img_mod = Image.fromarray(arr)
    img_mod.save(p_receipt)

    category = ClassifierEngine.classify_image(str(p_receipt))
    assert category == ImageCategory.DOCUMENT


def test_classify_batch_parallel(temp_workspace):
    p1 = temp_workspace / "screenshot_phone.png"
    p2 = temp_workspace / "store_receipt.jpg"
    p3 = temp_workspace / "standard_camera_photo.jpg"

    # Natural image with varied pixels
    arr = np.random.randint(40, 220, size=(200, 200, 3), dtype=np.uint8)
    Image.fromarray(arr).save(p3)

    results = ClassifierEngine.classify_batch([str(p1), str(p2), str(p3)])
    assert len(results) == 3
    assert results[str(p1)] == ImageCategory.SCREENSHOT
    assert results[str(p2)] == ImageCategory.DOCUMENT
    assert results[str(p3)] == ImageCategory.PHOTO
