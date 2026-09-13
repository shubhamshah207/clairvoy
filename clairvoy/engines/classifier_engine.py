"""
Clairvoy Image Classifier Engine
High-throughput, cascaded hybrid image categorization (Photos, Screenshots, Documents/Receipts, Graphics/Memes).
Combines instant hardware EXIF & spatial heuristics (Tier 1) with an open-source neural Vision-Language
model (OpenAI CLIP ViT-B/32 Quantized ONNX, Tier 2) for state-of-the-art accuracy and maximum CPU throughput.
"""

import os
import re
import threading
import urllib.request
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from clairvoy.core.classifier_data import get_category_prototypes
from clairvoy.core.config import (
    CLIP_DOWNLOAD_URL,
    CLIP_MODEL_FILE_PATH,
    DEFAULT_NUM_WORKERS,
    MAX_IMAGE_PIXELS,
    MODEL_CACHE_DIR,
)
from clairvoy.core.models import ImageCategory

try:
    from PIL import ExifTags, Image, ImageFile

    ImageFile.LOAD_TRUNCATED_IMAGES = True
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    import onnxruntime as ort

    HAS_ML = True
except ImportError:
    HAS_ML = False

# Common device screen aspect ratios (within 5% tolerance)
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

# Standard OpenAI CLIP normalization constants (broadcastable to [B, 3, 224, 224])
CLIP_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32).reshape(1, 3, 1, 1)
CLIP_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32).reshape(1, 3, 1, 1)


class ClassifierEngine:
    """
    Cascaded Hybrid Classifier:
    Tier 1 (Instant Heuristics, <0.2ms): Hardware EXIF, filename patterns, screen aspect ratios.
    Tier 2 (Neural Foundation Model, ~30ms): OpenAI CLIP ViT-B/32 Zero-Shot ONNX for ambiguous images.
    """

    _session: "ort.InferenceSession | None" = None
    _session_lock = threading.Lock()

    @classmethod
    def download_model(cls, force: bool = False) -> Path:
        """Downloads the quantized CLIP ViT-B/32 ONNX model (~85 MB) to local cache."""
        MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if force or not CLIP_MODEL_FILE_PATH.exists() or CLIP_MODEL_FILE_PATH.stat().st_size < 50_000_000:
            tmp_path = MODEL_CACHE_DIR / f"{CLIP_MODEL_FILE_PATH.name}.tmp.{os.getpid()}"
            print("[*] Downloading quantized OpenAI CLIP ViT-B/32 model (~85 MB)...")
            req = urllib.request.Request(
                CLIP_DOWNLOAD_URL,
                headers={"User-Agent": "Clairvoy-AI-Storage/0.1.0"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp, open(tmp_path, "wb") as f:
                while chunk := resp.read(1024 * 1024):
                    f.write(chunk)
            tmp_path.replace(CLIP_MODEL_FILE_PATH)
            print("[*] CLIP model successfully cached.")
        return CLIP_MODEL_FILE_PATH

    @classmethod
    def get_session(cls, auto_download: bool = False) -> "ort.InferenceSession | None":
        """Thread-safe lazy initialization of the ONNX Runtime session."""
        if not HAS_ML:
            return None

        if cls._session is not None:
            return cls._session

        with cls._session_lock:
            if cls._session is not None:
                return cls._session

            if not CLIP_MODEL_FILE_PATH.exists() or CLIP_MODEL_FILE_PATH.stat().st_size < 50_000_000:
                if auto_download:
                    cls.download_model()
                else:
                    return None

            try:
                opts = ort.SessionOptions()
                threads = min(os.cpu_count() or 4, 8)
                opts.intra_op_num_threads = threads
                opts.inter_op_num_threads = 2
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                cls._session = ort.InferenceSession(
                    str(CLIP_MODEL_FILE_PATH),
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
            except Exception as exc:
                print(f"[!] Warning: Could not initialize CLIP session: {exc}")
                cls._session = None

        return cls._session

    @classmethod
    def _classify_deterministic(cls, path: str) -> ImageCategory | None:
        """
        Tier 1: Instant hardware & filename check (<0.2ms).
        Returns ImageCategory if resolved with high certainty,
        or None if ambiguous and requires Tier 2 neural inspection.
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

                # Signal 2: Authentic camera hardware sensor EXIF tags
                exif = img.getexif()
                if exif:
                    for k in exif:
                        tag_name = ExifTags.TAGS.get(k, k)
                        if tag_name in CAMERA_HARDWARE_TAGS:
                            return ImageCategory.PHOTO

                # Signal 3: Standard phone/screen aspect ratios with lossless PNG format
                aspect = max(w, h) / max(1, min(w, h))
                is_screen_ratio = any(abs(aspect - r) < 0.04 for r in COMMON_SCREEN_RATIOS)
                ext = os.path.splitext(fn)[1].lower()

                if is_screen_ratio and ext in {".png", ".webp"}:
                    return ImageCategory.SCREENSHOT

                return None

        except Exception:
            return ImageCategory.FILE

    @classmethod
    def _classify_neural_paths(
        cls,
        paths: list[str],
        session: "ort.InferenceSession",
    ) -> list[ImageCategory]:
        """
        Tier 2: Batched neural forward pass using OpenAI CLIP ViT-B/32 ONNX.
        Processes paths in safe streaming batches without leaking file descriptors.
        """
        categories, prototype_matrix = get_category_prototypes()
        batch_tensors: list[np.ndarray] = []
        valid_indices: list[int] = []

        for idx, p in enumerate(paths):
            try:
                with Image.open(p) as img:
                    rgb_img = img.convert("RGB").resize((224, 224), Image.Resampling.BICUBIC)
                    arr = np.array(rgb_img, dtype=np.float32) / 255.0
                    batch_tensors.append(np.transpose(arr, (2, 0, 1)))
                    valid_indices.append(idx)
            except Exception:
                continue

        if not batch_tensors:
            return [ImageCategory.FILE] * len(paths)

        # Vectorized batch tensor [B, 3, 224, 224] normalized
        batch_np = np.stack(batch_tensors, axis=0)
        batch_np = (batch_np - CLIP_MEAN) / CLIP_STD

        # Run ONNX inference
        outputs = session.run(None, {"pixel_values": batch_np})
        embeddings = outputs[0]  # [B, 512]

        # L2-normalize visual embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.maximum(norms, 1e-12)

        # Dot product against [4, 512] prototype vectors -> [B, 4]
        sims = np.dot(embeddings, prototype_matrix.T)
        best_indices = np.argmax(sims, axis=1)

        result_cats = [ImageCategory.FILE] * len(paths)
        for valid_i, best_cat_i in zip(valid_indices, best_indices, strict=False):
            result_cats[valid_i] = categories[best_cat_i]

        return result_cats

    @classmethod
    def _classify_heuristic_pixel_path(cls, path: str) -> ImageCategory:
        """
        Graceful Tier 1 fallback when CLIP ONNX model is not present or offline.
        Uses whiteness ratio and color saturation differentials.
        """
        try:
            with Image.open(path) as img:
                thumb = img.convert("RGB").resize((128, 128), Image.Resampling.BILINEAR)
                arr = np.array(thumb, dtype=np.float32)

                # Whiteness ratio (Documents/Receipts have white background)
                white_pixels = (arr[:, :, 0] > 185) & (arr[:, :, 1] > 185) & (arr[:, :, 2] > 185)
                white_ratio = float(np.mean(white_pixels))

                # Color saturation difference
                color_diff = np.abs(arr[:, :, 0] - arr[:, :, 1]) + np.abs(arr[:, :, 1] - arr[:, :, 2])
                mean_saturation_diff = float(np.mean(color_diff))

                if white_ratio >= 0.40 and mean_saturation_diff < 45:
                    return ImageCategory.DOCUMENT

                flat_horizontal = np.mean(np.abs(np.diff(arr, axis=1)) < 2.0)
                flat_vertical = np.mean(np.abs(np.diff(arr, axis=0)) < 2.0)
                flat_ui_ratio = max(flat_horizontal, flat_vertical)

                if flat_ui_ratio > 0.35:
                    return ImageCategory.SCREENSHOT

                if mean_saturation_diff > 90 or flat_ui_ratio > 0.28:
                    return ImageCategory.GRAPHIC

                return ImageCategory.PHOTO
        except Exception:
            return ImageCategory.FILE

    @classmethod
    def classify_image(cls, path: str, use_neural: bool = True) -> ImageCategory:
        """
        Classifies a single image using the Cascaded Hybrid pipeline:
        1. Instant Tier 1 deterministic check (<0.2ms).
        2. Tier 2 Neural CLIP Zero-Shot check for ambiguous images.
        """
        cat = cls._classify_deterministic(path)
        if cat is not None:
            return cat

        session = cls.get_session() if use_neural else None
        if session is not None:
            results = cls._classify_neural_paths([path], session)
            return results[0]
        return cls._classify_heuristic_pixel_path(path)

    @classmethod
    def classify_batch(
        cls,
        image_paths: Iterable[str],
        num_workers: int = DEFAULT_NUM_WORKERS,
        use_neural: bool = True,
    ) -> dict[str, ImageCategory]:
        """
        High-throughput classification pipeline:
        1. Parallel Tier 1 deterministic classification across worker threads.
        2. Vectorized batch neural inference on ambiguous images via ONNX Runtime.
        Returns a dictionary mapping path -> ImageCategory.
        """
        paths_list = list(image_paths)
        if not paths_list:
            return {}

        results: dict[str, ImageCategory] = {}
        ambiguous_paths: list[str] = []

        # Step 1: Fast deterministic heuristic pass
        workers = min(len(paths_list), num_workers)
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            preliminary = list(pool.map(cls._classify_deterministic, paths_list))

        for path, cat in zip(paths_list, preliminary, strict=False):
            if cat is not None:
                results[path] = cat
            else:
                ambiguous_paths.append(path)

        # Step 2: Tier 2 Neural inference for ambiguous images
        if ambiguous_paths:
            session = cls.get_session() if use_neural else None

            if session is not None:
                batch_size = 32
                for i in range(0, len(ambiguous_paths), batch_size):
                    chunk_paths = ambiguous_paths[i : i + batch_size]
                    chunk_cats = cls._classify_neural_paths(chunk_paths, session)
                    for p, c in zip(chunk_paths, chunk_cats, strict=False):
                        results[p] = c
            else:
                # Heuristic pixel fallback
                for p in ambiguous_paths:
                    results[p] = cls._classify_heuristic_pixel_path(p)

        return results

