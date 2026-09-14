"""
Unit Tests for Vision Engine (DINOv2 ONNX)
"""

import numpy as np
import pytest

from clairvoy.engines.vision_engine import HAS_ML, DisjointSetUnion, VisionEngine


def test_disjoint_set_union():
    dsu = DisjointSetUnion(5)
    assert dsu.find(0) == 0
    assert dsu.find(1) == 1

    dsu.union(0, 1)
    assert dsu.find(0) == dsu.find(1)

    dsu.union(1, 2)
    assert dsu.find(0) == dsu.find(2)
    assert dsu.find(3) != dsu.find(0)


@pytest.mark.skipif(not HAS_ML, reason="ONNX Runtime or model dependencies missing")
def test_vision_preprocessing_and_inference(sample_images):
    red1 = str(sample_images["red1"])
    red2 = str(sample_images["red2"])
    blue = str(sample_images["blue"])

    engine = VisionEngine(threshold=0.90)

    # Test preprocessing
    tensor, dims = engine.preprocess_single_image(red1)
    assert tensor is not None
    assert tensor.shape == (3, 224, 224)
    assert dims == (300, 300)

    # Test embedding extraction
    embs = engine.extract_embeddings_batch([tensor, tensor])
    assert embs.shape == (2, 384)
    # Norm should be 1.0 (L2-normalized)
    assert np.isclose(np.linalg.norm(embs[0]), 1.0, atol=1e-5)

    # Test near duplicate clustering on sample images
    clusters = engine.find_near_duplicates([red1, red2, blue])
    # red1 and red2 should cluster together
    assert len(clusters) == 1
    cluster_paths = clusters[0][0]
    assert red1 in cluster_paths
    assert red2 in cluster_paths
    assert blue not in cluster_paths


def test_preprocess_palette_transparency(tmp_path):
    import warnings

    from PIL import Image

    # Create palette image with transparency
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
    palette_img = img.convert("P", palette=Image.Palette.ADAPTIVE)
    path = tmp_path / "transparent_palette.png"
    palette_img.save(path, format="PNG", transparency=0)

    engine = VisionEngine(threshold=0.90)
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        tensor, dims = engine.preprocess_single_image(str(path))
        # Ensure no UserWarning about Palette images with Transparency
        palette_warnings = [
            w for w in recorded if "Palette images with Transparency" in str(w.message)
        ]
        assert len(palette_warnings) == 0

    assert tensor is not None
    assert dims == (100, 100)

