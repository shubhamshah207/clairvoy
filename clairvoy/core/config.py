"""
Clairvoy Configuration & Constants
Centralized settings, directories, and model metadata.
"""

import os
from pathlib import Path

# Package Version
VERSION = "0.1.0"

# Defaults
DEFAULT_SIMILARITY_THRESHOLD: float = 0.95
DEFAULT_BATCH_SIZE: int = 32
DEFAULT_NUM_WORKERS: int = min(16, max(4, (os.cpu_count() or 4) * 2))

# Ignored directory names during filesystem scans
EXCLUDED_DIR_NAMES = {
    "_logs",
    "_zips",
    "_dedupe_reports",
    "_duplicate_quarantine",
    ".git",
    "__pycache__",
    ".vscode",
    ".idea",
    "$RECYCLE.BIN",
    "System Volume Information",
    "node_modules",
    ".venv",
    "venv",
}

# Supported image media formats for Vision AI
SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
    ".heic",
    ".psd",
}

# Supported video media formats
SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".ts",
    ".mp",
}

# Unified media extensions
SUPPORTED_MEDIA_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS

# DINOv2 ONNX Model Configuration
MODEL_DOWNLOAD_URL = (
    "https://huggingface.co/onnx-community/dinov2-small/resolve/main/onnx/model_quantized.onnx"
)
MODEL_CACHE_DIR = Path.home() / ".cache" / "clairvoy" / "models"
MODEL_FILENAME = "dinov2_small_quantized.onnx"
MODEL_FILE_PATH = MODEL_CACHE_DIR / MODEL_FILENAME
EXPECTED_MODEL_SIZE_BYTES = 24_451_000  # ~23.3 MB (tolerant range)

# CLIP ViT-B/32 Zero-Shot Classifier ONNX Model Configuration
CLIP_DOWNLOAD_URL = (
    "https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/main/onnx/vision_model_quantized.onnx"
)
CLIP_MODEL_FILENAME = "clip_vit_b32_quantized.onnx"
CLIP_MODEL_FILE_PATH = MODEL_CACHE_DIR / CLIP_MODEL_FILENAME
EXPECTED_CLIP_MODEL_SIZE_BYTES = 89_118_000  # ~85 MB

# Image processing limits (protection against decompression bombs)
MAX_IMAGE_PIXELS = 60_000_000

