"""
Clairvoy Vision Engine
High-throughput, local-first image similarity clustering powered by Meta DINOv2 ONNX.
"""

import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from clairvoy.core.config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_NUM_WORKERS,
    DEFAULT_SIMILARITY_THRESHOLD,
    MAX_IMAGE_PIXELS,
    MODEL_CACHE_DIR,
    MODEL_DOWNLOAD_URL,
    MODEL_FILE_PATH,
)

try:
    from PIL import Image, ImageFile
    # Allow loading truncated or slightly corrupted images safely
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    import onnxruntime as ort
    HAS_ML = True
except ImportError:
    HAS_ML = False


class DisjointSetUnion:
    """Disjoint Set Union (DSU) with path compression and union by rank."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, i: int) -> int:
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int) -> bool:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.rank[root_i] < self.rank[root_j]:
                self.parent[root_i] = root_j
            elif self.rank[root_i] > self.rank[root_j]:
                self.parent[root_j] = root_i
            else:
                self.parent[root_j] = root_i
                self.rank[root_i] += 1
            return True
        return False


class VisionEngine:
    """
    Computes L2-normalized DINOv2 vision embeddings and clusters near-duplicate photos.
    Runs 100% locally on CPU via ONNX Runtime without PyTorch.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        batch_size: int = DEFAULT_BATCH_SIZE,
        num_workers: int = DEFAULT_NUM_WORKERS,
    ):
        self.threshold = threshold
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.session: ort.InferenceSession | None = None

        if HAS_ML:
            self._init_session()

    def _ensure_model(self) -> Path:
        """Ensures the quantized DINOv2 ONNX model is securely downloaded and cached."""
        MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if not MODEL_FILE_PATH.exists() or MODEL_FILE_PATH.stat().st_size < 10_000_000:
            tmp_path = MODEL_CACHE_DIR / f"{MODEL_FILE_PATH.name}.tmp.{os.getpid()}"
            print("[*] Downloading quantized Meta DINOv2 model (~23 MB)...")
            req = urllib.request.Request(
                MODEL_DOWNLOAD_URL,
                headers={"User-Agent": "Clairvoy-AI-Storage/0.1.0"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp, open(tmp_path, "wb") as f:
                while chunk := resp.read(1024 * 1024):
                    f.write(chunk)

            # Atomic swap to prevent partial writes
            tmp_path.replace(MODEL_FILE_PATH)
            print("[*] Model successfully downloaded and cached.")

        return MODEL_FILE_PATH

    def _init_session(self) -> None:
        """Initializes high-performance ONNX Runtime inference session."""
        model_path = self._ensure_model()
        opts = ort.SessionOptions()
        threads = min(os.cpu_count() or 4, 8)
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 2
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        # Prefer CPU Execution Provider
        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )

    @staticmethod
    def preprocess_single_image(path: str) -> tuple[np.ndarray | None, tuple[int, int]]:
        """
        Loads, resizes, and standardizes an image tensor for DINOv2 input:
        Shape: (3, 224, 224), Mean: [0.485, 0.456, 0.406], Std: [0.229, 0.224, 0.225]
        """
        try:
            with Image.open(path) as img:
                w, h = img.size
                img = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
                arr = np.array(img, dtype=np.float32) / 255.0
                mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
                std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
                arr = (arr - mean) / std
                return np.transpose(arr, (2, 0, 1)), (w, h)
        except Exception:
            return None, (0, 0)

    def extract_embeddings_batch(self, batch_tensors: list[np.ndarray]) -> np.ndarray:
        """Runs batch inference and returns L2-normalized feature vectors."""
        if not self.session:
            raise RuntimeError("Vision inference session is not initialized.")

        batch_array = np.stack(batch_tensors)
        outputs = self.session.run(None, {"pixel_values": batch_array})
        # Extract [CLS] token embedding at index 0: shape (batch_size, 384)
        cls_embeddings = outputs[0][:, 0, :]
        norms = np.linalg.norm(cls_embeddings, axis=1, keepdims=True)
        return cls_embeddings / np.maximum(norms, 1e-12)

    def find_near_duplicates(
        self,
        image_paths: list[str],
    ) -> list[tuple[list[str], list[float], list[tuple[int, int]]]]:
        """
        Extracts embeddings across images concurrently, computes cosine similarity,
        and clusters near-duplicate groups using Disjoint Set Union (DSU).
        """
        if not HAS_ML or not self.session:
            print("[!] Vision AI dependencies or model session not available.")
            return []

        if not image_paths:
            return []

        print(f"[*] Extracting Vision AI embeddings for {len(image_paths)} photos...")
        t0 = time.time()

        valid_paths: list[str] = []
        dimensions: dict[str, tuple[int, int]] = {}
        embeddings_list: list[np.ndarray] = []

        # Step 1: Concurrent Preprocessing in chunks
        chunk_size = self.batch_size * 4
        with ThreadPoolExecutor(max_workers=self.num_workers) as pool:
            for i in range(0, len(image_paths), chunk_size):
                chunk = image_paths[i : i + chunk_size]
                results = list(pool.map(self.preprocess_single_image, chunk))

                batch_tensors: list[np.ndarray] = []
                batch_paths: list[str] = []

                for p, (tensor, dims) in zip(chunk, results, strict=False):
                    if tensor is not None:
                        batch_tensors.append(tensor)
                        batch_paths.append(p)
                        dimensions[p] = dims

                        if len(batch_tensors) >= self.batch_size:
                            embs = self.extract_embeddings_batch(batch_tensors)
                            embeddings_list.append(embs)
                            valid_paths.extend(batch_paths)
                            batch_tensors = []
                            batch_paths = []

                if batch_tensors:
                    embs = self.extract_embeddings_batch(batch_tensors)
                    embeddings_list.append(embs)
                    valid_paths.extend(batch_paths)

        if not embeddings_list:
            return []

        all_embs = np.vstack(embeddings_list)
        n_images = len(valid_paths)
        print(f"[*] Extracted {n_images} embeddings in {time.time() - t0:.1f}s.")
        print(f"[*] Clustering near-duplicates (threshold: {self.threshold * 100:.0f}%)...")

        # Step 2: Compute pairwise cosine similarity matrix
        sim_matrix = np.dot(all_embs, all_embs.T)

        # Step 3: Graph clustering with Disjoint Set Union
        dsu = DisjointSetUnion(n_images)
        for i in range(n_images):
            # Only examine upper triangle
            for j in range(i + 1, n_images):
                if sim_matrix[i, j] >= self.threshold:
                    dsu.union(i, j)

        # Group indices by root representative
        cluster_indices: dict[int, list[int]] = {}
        for idx in range(n_images):
            root = dsu.find(idx)
            cluster_indices.setdefault(root, []).append(idx)

        # Build final structured output
        clusters: list[tuple[list[str], list[float], list[tuple[int, int]]]] = []
        for root, indices in cluster_indices.items():
            if len(indices) > 1:
                group_paths = [valid_paths[idx] for idx in indices]
                # Similarity relative to root representative
                scores = [float(sim_matrix[root, idx]) for idx in indices]
                dims = [dimensions[p] for p in group_paths]
                clusters.append((group_paths, scores, dims))

        print(f"[✓] Clustered {len(clusters)} visual near-duplicate groups.")
        return clusters
