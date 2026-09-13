"""
Clairvoy Vision Core Engine (ML Near-Duplicate Detection)
Uses local Meta DINOv2 (quantized ONNX) embeddings and vector cosine similarity.
"""

import os
import urllib.request
import time
from collections import defaultdict
import numpy as np

try:
    from PIL import Image
    import onnxruntime as ort
    HAS_ML = True
except ImportError:
    HAS_ML = False

MODEL_URL = "https://huggingface.co/onnx-community/dinov2-small/resolve/main/onnx/model_quantized.onnx"
CACHE_DIR = os.path.expanduser("~/.cache/clairvoy/models")
MODEL_PATH = os.path.join(CACHE_DIR, "dinov2_small_quantized.onnx")

SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

class VisionEngine:
    def __init__(self, threshold=0.95):
        self.threshold = threshold
        self.session = None
        if HAS_ML:
            self._ensure_model()

    def _ensure_model(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        if not os.path.exists(MODEL_PATH):
            print(f"[*] Downloading local Vision AI model (DINOv2 Quantized, 23.3 MB)...")
            req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp, open(MODEL_PATH, "wb") as f:
                f.write(resp.read())
            print("[*] Model downloaded and cached locally.")

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(MODEL_PATH, sess_options=opts, providers=["CPUExecutionProvider"])

    def preprocess_image(self, path):
        """Preprocess image to [3, 224, 224] normalized tensor."""
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

    def extract_embeddings_batch(self, batch_tensors):
        """Run batch inference through DINOv2 and return L2-normalized embeddings."""
        batch_array = np.stack(batch_tensors)
        outputs = self.session.run(None, {"pixel_values": batch_array})
        # Extract [CLS] token embedding at index 0
        embeddings = outputs[0][:, 0, :]
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / np.maximum(norms, 1e-12)

    def find_near_duplicates(self, image_paths, batch_size=32):
        if not HAS_ML or not self.session:
            print("[!] ML dependencies or ONNX session missing.")
            return []

        print(f"[*] Generating visual embeddings for {len(image_paths)} photos...")
        start_time = time.time()
        
        valid_paths = []
        embeddings_list = []
        dimensions = {}

        current_batch = []
        current_paths = []

        for p in image_paths:
            tensor, (w, h) = self.preprocess_image(p)
            if tensor is not None:
                current_batch.append(tensor)
                current_paths.append(p)
                dimensions[p] = (w, h)

                if len(current_batch) >= batch_size:
                    embs = self.extract_embeddings_batch(current_batch)
                    embeddings_list.append(embs)
                    valid_paths.extend(current_paths)
                    current_batch = []
                    current_paths = []

        if current_batch:
            embs = self.extract_embeddings_batch(current_batch)
            embeddings_list.append(embs)
            valid_paths.extend(current_paths)

        if not embeddings_list:
            return []

        all_embs = np.vstack(embeddings_list)
        print(f"[*] Extracted {len(all_embs)} embeddings in {time.time() - start_time:.1f}s.")
        print(f"[*] Calculating similarity matrix (threshold: {self.threshold * 100:.0f}%)...")

        # Cosine similarity matrix via matrix multiplication (since vectors are L2-normalized)
        sim_matrix = np.dot(all_embs, all_embs.T)
        
        visited = set()
        clusters = []

        for i in range(len(valid_paths)):
            if i in visited:
                continue
            
            # Find indices with similarity >= threshold
            matches = np.where(sim_matrix[i] >= self.threshold)[0]
            if len(matches) > 1:
                group = [valid_paths[idx] for idx in matches]
                sim_scores = [float(sim_matrix[i][idx]) for idx in matches]
                clusters.append((group, sim_scores, [dimensions[p] for p in group]))
                for m in matches:
                    visited.add(m)

        print(f"[✓] Found {len(clusters)} visual near-duplicate clusters.")
        return clusters
