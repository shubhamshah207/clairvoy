# Drive E Multimodal Format Expansion Design Specification

- **Date:** 2026-09-13
- **Status:** Approved
- **Author:** Senior Staff Engineer / Antigravity Agent
- **Target Subsystem:** Clairvoy Matcher Plugins & Vision Engine

---

## 1. Executive Summary & Problem Context

Clairvoy is an ultra-fast, local-first multimodal deduplication engine. An audit of Drive E (`/mnt/e`) cataloged **70,204 files across 278.01 GB and 295 extensions**. 
While exact duplicates are handled via Tier 1 hashes, high-volume media and container formats required expansion to support visual and structural near-duplicate detection:
- **iPhone HEIC Photos (`.heic`):** 3,014 files (5.15 GB)
- **MPEG-TS Video Streams (`.ts`):** 647 files (7.78 GB total; 9 large video streams >900 MB, colliding in extension with TypeScript source code)
- **Photoshop Documents (`.psd`):** 32 files (1.51 GB)
- **Android / Java Packages (`.jar`, `.apk`):** 588 files (584.30 MB)
- **Google Pixel Motion Photos (`.mp` / `.MP`):** 16 files (137.21 MB)
- **RAR Archives (`.rar`):** 5 files (32.98 MB)

This specification defines the architectural design to integrate these formats into Clairvoy's existing deep module plugins without breaking modularity, introducing external cloud dependencies, or allowing false-positive matches (such as treating TypeScript code as video streams).

---

## 2. Architectural Design & Media Ingestion Flow

The design leverages **Modular Extension of Existing Deep Plugins** (Option 1). Rather than proliferating siloed plugins that prevent cross-format deduplication, media formats are mapped directly to their natural modality engines:

```
+----------------------------------------------------------------------------------------------------+
|                                    CLAIRVOY MEDIA INGESTION FLOW                                   |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|                                       [Input Files /mnt/e]                                         |
|                                                 |                                                  |
|         +---------------------------------------+---------------------------------------+          |
|         |                                       |                                       |          |
|         v                                       v                                       v          |
|  [Image Candidates]                      [Video Candidates]                    [Archive Candidates]|
|  .jpg, .png, .heic, .psd                 .mp4, .mkv, .mov, .ts, .mp            .zip, .jar, .apk    |
|         |                                       |                                       |          |
|         v                                       v                                       v          |
|  +-----------------------------+         +-----------------------------+         +---------------+ |
|  | PhotoVisionMatcherPlugin    |         | VideoKeyframeMatcherPlugin  |         | Archive-      | |
|  |                             |         |                             |         | Inspector     | |
|  | 1. .psd -> Pillow native    |         | 1. .ts -> Check sync byte   |         |               | |
|  | 2. .heic -> pillow-heif     |         |    0x47 (reject TypeScript) |         | Central-      | |
|  |    fallback: ffmpeg pipe    |         | 2. .mp -> Check ftyp box    |         | Directory     | |
|  | 3. Standardize to           |         | 3. ffprobe duration extract |         | CRC32 match   | |
|  |    (3, 224, 224) RGB tensor |         | 4. Extract sample keyframes |         | vs on-disk    | |
|  +--------------+--------------+         +--------------+--------------+         +-------+-------+ |
|                 |                                       |                                |         |
|                 v                                       v                                v         |
|  +-----------------------------+         +-----------------------------+                 |         |
|  | Meta DINOv2 ONNX Embeddings |         | Keyframe Hash & Timestamp   |                 |         |
|  | L2 Cosine Similarity        |         | Duration Tolerance Match    |                 |         |
|  +--------------+--------------+         +--------------+--------------+                 |         |
|                 |                                       |                                |         |
|                 +---------------------------------------+--------------------------------+         |
|                                                         |                                          |
|                                                         v                                          |
|                                             [Disjoint Set Union (DSU)]                             |
|                                                         |                                          |
|                                                         v                                          |
|                                       [Cross-Format Duplicate Clusters]                            |
|                                        e.g., .jpg <-> .heic <-> .psd                               |
|                                        e.g., .mp4 <-> .ts   <-> .mp                                |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Component Specifications

### 3.1. Vision Engine & Photo Vision Matcher
- **Target Files:** [`clairvoy/engines/vision_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/vision_engine.py), [`clairvoy/plugins/photo_vision.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py)
- **Supported Extensions:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.tif`, `.heic`, `.psd` (case-insensitive).
- **Photoshop PSD Support:**
  - Handled directly in Pillow (`Image.open(path)`).
  - Pillow reads the flattened composite channel and returns RGBA / RGB data.
  - Converted to standard RGB `(3, 224, 224)` normalized float tensor.
- **HEIC Dual-Path Decoding:**
  - *Fast Path:* Attempt `Image.open(path)`. If `pillow-heif` is present and registered, Pillow decodes it directly in-process.
  - *Zero-Dependency Fallback:* If Pillow raises `UnidentifiedImageError`, invoke static local `ffmpeg`:
    ```bash
    ffmpeg -v error -i <path> -vframes 1 -f image2pipe -vcodec rawvideo -pix_fmt rgb24 -
    ```
    Read the raw RGB buffer via subprocess pipe with a 10-second timeout, construct a Pillow Image via `Image.frombytes("RGB", (w, h), raw_bytes)`, and resize to standard `(224, 224)` tensor.

### 3.2. Video Keyframe Matcher & Stream Validation
- **Target Files:** [`clairvoy/plugins/video_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py)
- **Supported Extensions:** `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.wmv`, `.m4v`, `.ts`, `.mp` (case-insensitive).
- **MPEG-TS Sync-Byte Discriminator (`is_mpeg_ts`):**
  - Reads 376 bytes from the file header.
  - Checks that `header[0] == 0x47` and `header[188] == 0x47` (MPEG-TS standard 188-byte packet synchronization).
  - Rejects text files (e.g. TypeScript `.ts`) instantly in $<0.1\,\text{ms}$.
- **Pixel Motion Photo Discriminator (`is_motion_photo_or_mp4`):**
  - Reads first 32 bytes to identify `b"ftyp"` MP4 container box.
  - If valid, handles as video clip; otherwise skips.
- **Matching Pipeline:**
  - Duration extracted via `ffprobe` format duration entry.
  - Keyframes extracted at 10%, 50%, and 90% timestamps.
  - Video streams are clustered using duration tolerance ($\pm 2\,\text{s}$ or $2\%$) and keyframe visual similarity.

### 3.3. Archive Inspector Matcher
- **Target Files:** [`clairvoy/plugins/archive_inspector.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py)
- **Supported Extensions:** `.zip`, `.jar`, `.apk`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`, `.rar` (case-insensitive).
- **In-Memory ZIP Central Directory Inspection:**
  - `.jar` and `.apk` are standard ZIP packages.
  - Processed using Python's built-in `zipfile.ZipFile(archive_path, 'r')`.
  - Compares candidate files on disk against archive member file sizes and CRC32 checksums without writing extracted files to disk.
- **RAR Archive Handling:**
  - Identifies RAR header magic signatures: `b"Rar!\x1a\x07\x00"` (RAR4) and `b"Rar!\x1a\x07\x01\x00"` (RAR5).
  - If optional library `rarfile` or `unrar` binary is present, inspects central directory.
  - If missing, logs informational notice and skips gracefully without failing the pipeline.

---

## 4. Error Handling & Invariants

1. **Zero Unauthenticated Cloud Calls:** 100% of processing runs locally on CPU / system binaries.
2. **Decompression Bomb Protection:** `Image.MAX_IMAGE_PIXELS = 178_956_970` is enforced to prevent memory exhaustion attacks.
3. **Subprocess Isolation & Timeouts:** All `ffmpeg` / `ffprobe` calls must specify `timeout=10` or `timeout=15` and capture stderr. Any timeout or exit code $\ne 0$ logs a debug warning and returns fallback `None`.
4. **Graceful Degradation:** A corrupted frame in an image or video does not stop the batch; `preprocess_single_image` returns `(None, (0, 0))` and continues processing valid items.
5. **Continuous Documentation:** Maintain [`AGENTS.md`](file:///home/shubhamshah207/clairvoy/AGENTS.md), [`docs/ARCHITECTURE.md`](file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md), and [`docs/PLUGINS.md`](file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md).

---

## 5. Test & Verification Plan

1. **Unit Tests ([`tests/test_format_expansion.py`](file:///home/shubhamshah207/clairvoy/tests/test_format_expansion.py)):**
   - MPEG-TS sync-byte detection accepts binary `.ts` with `0x47` packets and rejects TypeScript text files.
   - Motion photo discriminator accepts `ftyp` `.mp` files and rejects text.
   - Pillow loads `.psd` files and outputs normalized DINOv2 tensors.
   - HEIC fallback extraction via `ffmpeg` pipe generates valid RGB tensors.
   - Archive inspector peeks inside `.jar` and `.apk` archives and accurately matches CRC32 checksums against mock on-disk candidates.
2. **End-to-End Regression:**
   - Full pytest suite: `/home/shubhamshah207/miniconda3/bin/pytest -v` (all tests passing).
   - Code style and linting: `/home/shubhamshah207/miniconda3/bin/ruff check .` (0 errors).
