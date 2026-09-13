"""
Clairvoy Image Classifier Engine
High-throughput, local-first image categorization (Screenshots, Documents/Receipts, Photos, Memes/Graphics).
Operates 100% offline using multi-signal EXIF inspection, screen aspect ratios, and color space analytics.
"""

import os
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import ExifTags, Image

from clairvoy.core.config import DEFAULT_NUM_WORKERS
from clairvoy.core.models import ImageCategory

# Common device screen aspect ratios (within 4% tolerance)
COMMON_SCREEN_RATIOS = [
    16 / 9,     # 1.778 (1920x1080, 1280x720)
    18 / 9,     # 2.000 (2160x1080)
    19.5 / 9,   # 2.167 (iPhone X/11/12/13/14/15, modern Samsung/Pixel)
    20 / 9,     # 2.222 (2400x1080 OnePlus/Xiaomi/Samsung Galaxy)
    16 / 10,    # 1.600 (MacBook, Android Tablets)
    4 / 3,      # 1.333 (iPad, PC monitors)
]

CAMERA_HARDWARE_TAGS = {
    "Make",
    "Model",
    "FNumber",
    "ExposureTime",
    "ISOSpeedRatings",
    "FocalLength",
    "LensModel",
}

SCREENSHOT_NAME_PATTERNS = re.compile(
    r"(screenshot|screen_shot|screen-shot|screencap|snip|capture|screen\s*shot)",
    re.IGNORECASE,
)

DOCUMENT_NAME_PATTERNS = re.compile(
    r"(receipt|invoice|bill|scan|document|tax|form|whiteboard|license|statement|ticket|page_\d+|doc_)",
    re.IGNORECASE,
)

GRAPHIC_NAME_PATTERNS = re.compile(
    r"(meme|comic|sticker|vector|logo|illustration|clipart|infographic|banner)",
    re.IGNORECASE,
)


class ClassifierEngine:
    """Classifies images into Photos, Screenshots, Documents/Receipts, or Graphics."""

    @classmethod
    def classify_image(cls, path: str) -> ImageCategory:
        """
        Classifies a single image using multi-signal analysis:
        1. Filename & path tokens
        2. Hardware camera EXIF metadata
        3. Screen aspect ratio & device resolutions
        4. Photometric brightness, saturation, and UI flat-region analytics
        """
        fn = os.path.basename(path)

        # Signal 1: Explicit filename keywords
        if SCREENSHOT_NAME_PATTERNS.search(fn):
            return ImageCategory.SCREENSHOT
        if DOCUMENT_NAME_PATTERNS.search(fn):
            return ImageCategory.DOCUMENT
        if GRAPHIC_NAME_PATTERNS.search(fn):
            return ImageCategory.GRAPHIC

        try:
            with Image.open(path) as img:
                w, h = img.size
                if w <= 0 or h <= 0:
                    return ImageCategory.FILE

                # Signal 2: Camera Hardware EXIF
                has_camera_hardware = False
                exif = img.getexif()
                if exif:
                    for k, _ in exif.items():
                        tag_name = ExifTags.TAGS.get(k, k)
                        if tag_name in CAMERA_HARDWARE_TAGS:
                            has_camera_hardware = True
                            break

                # Signal 3: Aspect Ratio Check
                aspect = max(w, h) / max(1, min(w, h))
                is_screen_aspect = any(abs(aspect - r) < 0.05 for r in COMMON_SCREEN_RATIOS)

                # Signal 4: Color Space & Gradient Analytics on downscaled thumbnail
                thumb = img.convert("RGB").resize((128, 128), Image.Resampling.BILINEAR)
                arr = np.array(thumb, dtype=np.float32)

                # Whiteness ratio (Documents have white/off-white backgrounds)
                white_pixels = (arr[:, :, 0] > 185) & (arr[:, :, 1] > 185) & (arr[:, :, 2] > 185)
                white_ratio = float(np.mean(white_pixels))

                # Color saturation difference (Documents/Receipts are near-monochrome with dark ink)
                color_diff = np.abs(arr[:, :, 0] - arr[:, :, 1]) + np.abs(arr[:, :, 1] - arr[:, :, 2])
                mean_saturation_diff = float(np.mean(color_diff))

                # Document / Receipt Detection
                if white_ratio >= 0.40 and mean_saturation_diff < 45:
                    return ImageCategory.DOCUMENT

                # Flat color regions (Screenshots have large solid toolbars, navbars, or app backgrounds)
                flat_horizontal = np.mean(np.abs(np.diff(arr, axis=1)) < 2.0)
                flat_vertical = np.mean(np.abs(np.diff(arr, axis=0)) < 2.0)
                flat_ui_ratio = max(flat_horizontal, flat_vertical)

                # Screenshot Detection: Screen ratio + solid UI blocks + no camera hardware
                if (is_screen_aspect and flat_ui_ratio > 0.22 and not has_camera_hardware) or (
                    flat_ui_ratio > 0.35 and not has_camera_hardware
                ):
                    return ImageCategory.SCREENSHOT

                # Graphic / Meme Detection: High saturation or bold flat colors without camera hardware
                if not has_camera_hardware and (mean_saturation_diff > 90 or flat_ui_ratio > 0.28):
                    return ImageCategory.GRAPHIC

                # Camera photo (either has EXIF or continuous natural gradients)
                return ImageCategory.PHOTO

        except Exception:
            return ImageCategory.FILE

    @classmethod
    def classify_batch(
        cls,
        image_paths: Iterable[str],
        num_workers: int = DEFAULT_NUM_WORKERS,
    ) -> dict[str, ImageCategory]:
        """
        Classifies multiple image paths concurrently across worker threads.
        Returns a dictionary mapping path -> ImageCategory.
        """
        paths_list = list(image_paths)
        if not paths_list:
            return {}

        results: dict[str, ImageCategory] = {}
        workers = min(len(paths_list), num_workers)

        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            categories = list(pool.map(cls.classify_image, paths_list))

        for p, cat in zip(paths_list, categories, strict=False):
            results[p] = cat

        return results
