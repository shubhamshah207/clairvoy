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
        threads = min(os.cpu_count() or 4, 4)
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        # Prefer CPU Execution Provider
        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )

    @staticmethod
    def _extract_frame_via_ffmpeg(path: str) -> Image.Image | None:
        """Extract a single frame from an image or video file using local ffmpeg pipe."""
        import shutil
        import subprocess

        ffmpeg_bin = shutil.which("ffmpeg") or "/home/shubhamshah207/.local/bin/ffmpeg"
        if not shutil.which("ffmpeg") and not Path(ffmpeg_bin).exists():
            return None
        try:
            # Scale directly during ffmpeg decode to raw 224x224 RGB bytes to minimize pipe memory & latency
            cmd = [
                str(ffmpeg_bin),
                "-v",
                "error",
                "-threads",
                "1",
                "-i",
                path,
                "-vf",
                "scale=224:224:force_original_aspect_ratio=increase,crop=224:224",
                "-vframes",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=10)
            if res.returncode == 0 and len(res.stdout) == 224 * 224 * 3:
                return Image.frombytes("RGB", (224, 224), res.stdout)
        except Exception:
            return None
        return None

    @staticmethod
    def preprocess_single_image(path: str) -> tuple[np.ndarray | None, tuple[int, int]]:
        """
        Loads, resizes, and standardizes an image tensor for DINOv2 input:
        Shape: (3, 224, 224), Mean: [0.485, 0.456, 0.406], Std: [0.229, 0.224, 0.225]
        Supports .jpg, .png, .webp, .psd, and .heic (via Pillow or ffmpeg fallback).
        Memory safe: uses draft decoding on JPEGs, handles palette transparency cleanly,
        and ensures image contexts and file handles are closed promptly.
        """
        try:
            ext = Path(path).suffix.lower()
            img: Image.Image | None = None
            w, h = 0, 0

            if ext in {".heic", ".heif"}:
                try:
                    with Image.open(path) as pil_img:
                        w, h = pil_img.size
                        pil_img.load()
                        img = pil_img.copy()
                except Exception:
                    img = VisionEngine._extract_frame_via_ffmpeg(path)
                    if img is not None:
                        w, h = img.size
            else:
                try:
                    with Image.open(path) as pil_img:
                        w, h = pil_img.size
                        if ext in {".jpg", ".jpeg"}:
                            import contextlib

                            with contextlib.suppress(Exception):
                                pil_img.draft("RGB", (224, 224))
                        # Convert palette transparency cleanly to avoid PIL UserWarning
                        if pil_img.mode == "P" and "transparency" in pil_img.info:
                            converted = pil_img.convert("RGBA").convert("RGB")
                        else:
                            converted = pil_img.convert("RGB")
                        img = converted.resize((224, 224), Image.Resampling.BILINEAR)
                except Exception:
                    return None, (0, 0)

            if img is None:
                return None, (0, 0)

            if img.size != (224, 224):
                img = img.resize((224, 224), Image.Resampling.BILINEAR)

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

        # Step 1: Concurrent Preprocessing in chunks with bounded concurrency
        chunk_size = self.batch_size * 4
        preprocess_workers = min(4, self.num_workers)
        with ThreadPoolExecutor(max_workers=preprocess_workers) as pool:
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

                # Periodically release memory and unreferenced C buffers
                if (i // chunk_size) % 5 == 0:
                    import gc

                    gc.collect()

        if not embeddings_list:
            return []

        all_embs = np.vstack(embeddings_list)
        n_images = len(valid_paths)
        print(f"[*] Extracted {n_images} embeddings in {time.time() - t0:.1f}s.")
        print(f"[*] Clustering near-duplicates (threshold: {self.threshold * 100:.0f}%)...")

        # Step 2: Memory-efficient chunked dot-products with Disjoint Set Union
        dsu = DisjointSetUnion(n_images)
        chunk_size = 1024

        for i_start in range(0, n_images, chunk_size):
            i_end = min(i_start + chunk_size, n_images)
            chunk_sim = np.dot(all_embs[i_start:i_end], all_embs.T)

            # Mask out self-matches and lower triangle
            for r in range(i_end - i_start):
                chunk_sim[r, : i_start + r + 1] = 0.0

            rows, cols = np.where(chunk_sim >= self.threshold)
            for r, c in zip(rows, cols, strict=False):
                dsu.union(i_start + r, c)

        # Step 3: Group indices by root representative
        cluster_indices: dict[int, list[int]] = {}
        for idx in range(n_images):
            root = dsu.find(idx)
            cluster_indices.setdefault(root, []).append(idx)

        # Build final structured output
        clusters: list[tuple[list[str], list[float], list[tuple[int, int]]]] = []
        for root, indices in cluster_indices.items():
            if len(indices) > 1:
                group_paths = [valid_paths[idx] for idx in indices]
                # Compute exact similarity of cluster members relative to root representative
                root_emb = all_embs[root : root + 1]
                member_embs = all_embs[indices]
                member_sims = np.dot(root_emb, member_embs.T).squeeze(0)
                scores = [float(s) for s in member_sims]
                dims = [dimensions[p] for p in group_paths]
                clusters.append((group_paths, scores, dims))

        print(f"[✓] Clustered {len(clusters)} visual near-duplicate groups.")
        return clusters

