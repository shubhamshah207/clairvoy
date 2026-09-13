"""
Clairvoy Classifier Data & Prototypes
Pre-computed zero-shot text prototype embeddings (512-dim) for OpenAI CLIP ViT-B/32.
Enables high-throughput zero-shot inference without requiring runtime tokenizers or text models.
"""

from pathlib import Path

import numpy as np

from clairvoy.core.models import ImageCategory

_PROTOTYPES_FILE = Path(__file__).parent / "classifier_prototypes.npz"

_CACHED_CATEGORIES: list[ImageCategory] | None = None
_CACHED_MATRIX: np.ndarray | None = None


def get_category_prototypes() -> tuple[list[ImageCategory], np.ndarray]:
    """
    Returns ordered list of ImageCategory enums and their [N, 512] float32 normalized
    prototype embedding matrix. Caches result in memory after first load.
    """
    global _CACHED_CATEGORIES, _CACHED_MATRIX

    if _CACHED_MATRIX is not None and _CACHED_CATEGORIES is not None:
        return _CACHED_CATEGORIES, _CACHED_MATRIX

    categories = [
        ImageCategory.PHOTO,
        ImageCategory.SCREENSHOT,
        ImageCategory.DOCUMENT,
        ImageCategory.GRAPHIC,
    ]

    if _PROTOTYPES_FILE.exists():
        with np.load(_PROTOTYPES_FILE) as data:
            vectors = [data[cat.name] for cat in categories]
            matrix = np.stack(vectors, axis=0).astype(np.float32)
            # Ensure unit normalized
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            matrix = matrix / np.maximum(norms, 1e-12)
            _CACHED_CATEGORIES = categories
            _CACHED_MATRIX = matrix
            return _CACHED_CATEGORIES, _CACHED_MATRIX

    # Fallback to zero matrix if npz missing
    _CACHED_CATEGORIES = categories
    _CACHED_MATRIX = np.zeros((len(categories), 512), dtype=np.float32)
    return _CACHED_CATEGORIES, _CACHED_MATRIX
