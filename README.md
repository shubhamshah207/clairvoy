# Clairvoy 👁️

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)]()

> **Clairvoy** (*from Clairvoyance — clear perception*) is a local-first, AI-powered storage deduplication engine with both a headless **CLI** and an interactive **Web App UI**.
> It combines lightning-fast byte hashing for general files with Vision Transformer embeddings to catch near-duplicate photos, burst shots, and re-encoded videos.

---

## 🏛️ Architecture

```text
+-------------------------------------------------------------------------+
|                           USER INTERFACES                               |
|                                                                         |
|    [ 1. Terminal CLI: `clairvoy scan` ]     [ 2. Web App: localhost ]  |
|         (Headless, scriptable, cron)          (Modern Browser UI)       |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  FASTAPI BACKEND & EVENT STREAM (SSE)                   |
|                                                                         |
|   • REST API endpoints (`/api/scan`, `/api/duplicates`, `/api/action`)  |
|   • Live progress streaming via Server-Sent Events                      |
|   • Local SQLite cache (`clairvoy.db`) for instant incremental re-scans |
+-------------------------------------------------------------------------+
                                     |
                +--------------------+--------------------+
                |                                         |
                v                                         v
+-------------------------------+       +-------------------------------+
|     ENGINE 1: STORAGE CORE    |       |       ENGINE 2: ML VISION     |
|    (Czkawka CLI / Fast Hash)  |       |   (DINOv2 + FAISS / ONNX)     |
|                               |       |                               |
| • Byte-for-byte exact hash    |       | • Offline Vision Transformer  |
| • Filename normalization      |       | • Burst-shot detection        |
| • Non-media & general files   |       | • Angle & crop similarity     |
| • Broken & empty files        |       | • Visual vector cosine search |
+-------------------------------+       +-------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                         WEB APP FEATURES                                |
|                                                                         |
|   • Categorized Dashboard: Exact Duplicates, Similar Photos, Large Files|
|   • Interactive Visual Diff: Side-by-side photo comparison with slider  |
|   • 1-Click Smart Clean: Pre-selects best quality / resolution keeper   |
|   • Non-Destructive Quarantine with 1-Click Rollback                    |
+-------------------------------------------------------------------------+
```

---

## ✨ Features

- ⚡ **Two-Stage Hybrid Engine**:
  - **Stage 1 (Storage Core):** Filters 80–90% of duplicates in seconds using size grouping, quick-hash (header/footer 64KB), and full SHA-256 content verification.
  - **Stage 2 (Vision AI Core):** Applies lightweight, offline Vision Transformer embeddings (DINOv2 / ONNX) to discover burst shots, resized images, and color-graded duplicates.
- 🌐 **Interactive Web App UI**:
  - Launch with `clairvoy ui` to review duplicate pairs side-by-side in your browser.
  - Adjust similarity thresholds dynamically with an interactive slider.
- 🛡️ **Non-Destructive Quarantine**:
  - Never permanently deletes without confirmation.
  - Safely moves duplicates to a designated `_quarantine/` folder with an automated 1-click rollback manifest.
- 🔒 **100% Local & Privacy-Preserving**:
  - Zero cloud dependencies, zero telemetry.
  - All ML models run strictly on your local CPU / GPU.

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/shubhamshah207/clairvoy.git
cd clairvoy

# Install in editable mode
pip install -e .

# (Optional) Install ML dependencies for deep vision clustering
pip install -e ".[ml]"
```

### 1. Terminal CLI Usage

```bash
# Fast deduplication scan of a directory
clairvoy scan /path/to/storage

# Scan with safe quarantine (moves duplicates instead of deleting)
clairvoy scan /path/to/storage --quarantine

# Generate JSON and CSV reports only
clairvoy report /path/to/storage --output ./reports
```

### 2. Interactive Web App Usage

```bash
# Start the local web interface
clairvoy ui --port 8000
```
Open **`http://localhost:8000`** in your browser to inspect duplicates side-by-side.

---

## 🗺️ Roadmap

- [x] Initial project design and architecture
- [x] Fast Content Hash & Metadata Deduplication Engine
- [ ] DINOv2 ONNX quantized vision model integration
- [ ] FastAPI backend + Server-Sent Events progress reporting
- [ ] Interactive Web App review dashboard with visual side-by-side diff
- [ ] PyPI automated release pipeline via GitHub Actions

---

## 📄 License

Licensed under the [Apache License, Version 2.0](./LICENSE).
