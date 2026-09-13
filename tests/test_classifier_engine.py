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


def test_classify_by_camera_exif(temp_workspace):
    # Camera photo with Sony EXIF tags
    p_photo = temp_workspace / "nature_vacation.jpg"
    img = Image.new("RGB", (400, 300), color=(120, 160, 200))
    exif = img.getexif()
    exif[0x010F] = "Sony"  # Make
    exif[0x0110] = "ILCE-7M4"  # Model
    img.save(p_photo, exif=exif)

    assert ClassifierEngine.classify_image(str(p_photo)) == ImageCategory.PHOTO


def test_classify_document_by_whiteness(temp_workspace):
    # A scanned page or receipt: predominantly white with black text lines
    p_receipt = temp_workspace / "paper_scan.jpg"
    img = Image.new("RGB", (300, 400), color=(250, 250, 250))
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

    Image.new("RGB", (1080, 2340), color=(50, 50, 50)).save(p1)

    img2 = Image.new("RGB", (300, 400), color=(250, 250, 250))
    arr2 = np.array(img2)
    arr2[100:110, 50:250] = (20, 20, 20)
    Image.fromarray(arr2).save(p2)

    img3 = Image.new("RGB", (400, 300), color=(100, 140, 180))
    exif = img3.getexif()
    exif[0x010F] = "Apple"
    exif[0x0110] = "iPhone 15 Pro"
    img3.save(p3, exif=exif)

    results = ClassifierEngine.classify_batch([str(p1), str(p2), str(p3)])
    assert len(results) == 3
    assert results[str(p1)] == ImageCategory.SCREENSHOT
    assert results[str(p2)] == ImageCategory.DOCUMENT
    assert results[str(p3)] == ImageCategory.PHOTO


def test_neural_clip_inference(temp_workspace):
    p_img = temp_workspace / "ambiguous_file_001.jpg"
    img = Image.new("RGB", (300, 400), color=(250, 250, 250))
    arr = np.array(img)
    for y in range(40, 360, 20):
        arr[y : y + 3, 30:270] = (15, 15, 15)
    Image.fromarray(arr).save(p_img)

    cat = ClassifierEngine.classify_image(str(p_img), use_neural=True)
    assert cat in {ImageCategory.DOCUMENT, ImageCategory.PHOTO, ImageCategory.SCREENSHOT, ImageCategory.GRAPHIC}

