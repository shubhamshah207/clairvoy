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
- 🏷️ **Automatic Image Classification**:
  - Automatically identifies and categorizes images into **Screenshots**, **Documents & Receipts**, **Camera Photos**, and **Graphics/Memes**.
  - Uses multi-signal EXIF hardware analysis, screen aspect ratio detection, and color space analytics.
  - Interactive category filter tabs directly in the Web UI.
- 🌐 **Interactive Web App UI**:
  - Launch with `clairvoy ui` to review duplicate pairs side-by-side in your browser.
  - Adjust similarity thresholds dynamically with an interactive slider.
  - Filter duplicates by category (e.g. view and clean only screenshots or receipts).
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
# High-speed scan of a single folder
clairvoy scan /path/to/storage

# Concurrent multi-path scan across multiple storage remotes / drives
clairvoy scan /mnt/e/Remotes/gdrive-srshah207 /mnt/e/Remotes/gphotos-shubhamshah207 /mnt/e/Backup

# Tune visual similarity threshold (e.g. 90%) and parallel worker threads
clairvoy scan /path1 /path2 --threshold 0.90 --workers 16

# Scan general documents only (disables ML vision model)
clairvoy scan /path/to/storage --no-ml

# Safely isolate duplicates into _duplicate_quarantine with rollback manifest
clairvoy quarantine /path/to/storage/_dedupe_reports/duplicates_summary.json

# 1-Click Rollback / Restore quarantined files in parallel
clairvoy restore /path/to/storage/_duplicate_quarantine/quarantine_manifest.json
```

### 2. Interactive Web App Usage

```bash
# Launch local Web App dashboard
clairvoy ui --port 8000
```
Open **`http://localhost:8000`** in your browser to inspect duplicates side-by-side, view thumbnails, and execute 1-click safe quarantine.

---

## 🧪 Testing

```bash
# Install development and test dependencies
pip install -e ".[dev,ml]"

# Run full unit and integration test suite
pytest -v
```

---

## 🗺️ Roadmap

- [x] Initial project design and architecture
- [x] Fast Content Hash & Metadata Deduplication Engine (QuickHash + SHA-256)
- [x] Local Meta DINOv2 ONNX quantized vision model integration
- [x] FastAPI backend + async background scan engine
- [x] Interactive Web App review dashboard with visual side-by-side diff
- [x] Reversible quarantine engine with rollback manifests
- [x] Directory traversal security shield and strict path validation
- [x] Automated unit and integration test suite (100% passing)
- [ ] PyPI automated release pipeline via GitHub Actions

---

## 📄 License

Licensed under the [Apache License, Version 2.0](./LICENSE).
