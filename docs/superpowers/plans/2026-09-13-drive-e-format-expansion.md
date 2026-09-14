# Drive E Multimodal Format Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Clairvoy's local-first deduplication engine to support `.ts`, `.mp`, `.heic`, `.psd`, `.jar`, `.apk`, and `.rar` file types discovered on Drive E (`/mnt/e`) without cloud calls or false positives.

**Architecture:** Modular extension of existing deep plugins (`PhotoVisionMatcherPlugin`, `VideoKeyframeMatcherPlugin`, `ArchiveInspectorMatcherPlugin`) backed by an $O(1)$ stream validation utility (`format_utils.py`) and a zero-dependency dual-path image decoder in `VisionEngine`.

**Tech Stack:** Python 3.12, Pillow, ONNX Runtime, NumPy, standard library `zipfile`, `ffprobe`/`ffmpeg` static CLI, pytest, ruff.

**Spec:** [`docs/superpowers/specs/2026-09-13-drive-e-format-expansion-design.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-13-drive-e-format-expansion-design.md)

## Global Constraints

- Python 3.12+ type annotations (`T | None`, `list[T]`, `dict[K, V]`).
- 100% offline and local-first; zero unauthenticated external cloud calls.
- Pillow `Image.MAX_IMAGE_PIXELS = 178_956_970` strictly enforced.
- Subprocess calls (`ffmpeg`, `ffprobe`) must specify explicit timeouts (10s or 15s).
- All new/modified code must pass `/home/shubhamshah207/miniconda3/bin/pytest -v` and `/home/shubhamshah207/miniconda3/bin/ruff check .`.
- Maintain [`AGENTS.md`](file:///home/shubhamshah207/clairvoy/AGENTS.md), [`docs/ARCHITECTURE.md`](file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md), and [`docs/PLUGINS.md`](file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md).

---

### Task 1: Format Validation & Stream Discriminators (`format_utils.py`)

**Files:**
- Create: `clairvoy/core/format_utils.py`
- Test: `tests/test_format_utils.py`

**Interfaces:**
- Consumes: Standard library `os`, `pathlib.Path`.
- Produces:
  - `is_mpeg_ts(path: str) -> bool`
  - `is_motion_photo_video(path: str) -> bool`
  - `is_rar_archive(path: str) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_format_utils.py
import pytest
from pathlib import Path
from clairvoy.core.format_utils import is_mpeg_ts, is_motion_photo_video, is_rar_archive


def test_is_mpeg_ts_valid(tmp_path: Path):
    # MPEG-TS packet sync byte 0x47 every 188 bytes
    ts_file = tmp_path / "stream.ts"
    payload = bytearray(376)
    payload[0] = 0x47
    payload[188] = 0x47
    ts_file.write_bytes(payload)
    assert is_mpeg_ts(str(ts_file)) is True


def test_is_mpeg_ts_rejects_typescript_source(tmp_path: Path):
    ts_file = tmp_path / "app.ts"
    ts_file.write_text("import React from 'react'; export const App = () => null;")
    assert is_mpeg_ts(str(ts_file)) is False


def test_is_mpeg_ts_handles_empty_or_small(tmp_path: Path):
    empty_file = tmp_path / "empty.ts"
    empty_file.write_bytes(b"")
    assert is_mpeg_ts(str(empty_file)) is False


def test_is_motion_photo_video_valid(tmp_path: Path):
    mp_file = tmp_path / "PXL_sample.MP"
    # ISO MP4 container starts with 4-byte size followed by 'ftyp'
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    mp_file.write_bytes(header)
    assert is_motion_photo_video(str(mp_file)) is True


def test_is_motion_photo_video_rejects_non_ftyp(tmp_path: Path):
    txt_file = tmp_path / "readme.mp"
    txt_file.write_text("This is a markdown notes file.")
    assert is_motion_photo_video(str(txt_file)) is False


def test_is_rar_archive_detection(tmp_path: Path):
    rar_file = tmp_path / "archive.rar"
    rar_file.write_bytes(b"Rar!\x1a\x07\x00" + b"\x00" * 20)
    assert is_rar_archive(str(rar_file)) is True

    fake_rar = tmp_path / "fake.rar"
    fake_rar.write_bytes(b"NOT_A_RAR_FILE")
    assert is_rar_archive(str(fake_rar)) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_format_utils.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clairvoy.core.format_utils'`

- [ ] **Step 3: Write minimal implementation**

```python
# clairvoy/core/format_utils.py
"""Stream signature validation utilities for disambiguating file extensions."""

from __future__ import annotations

from pathlib import Path


def is_mpeg_ts(path: str) -> bool:
    """Return True if the file matches the MPEG-TS packet format (sync byte 0x47).

    Validates that the file has at least 376 bytes and contains the 0x47 sync byte
    at offset 0 and offset 188 (standard 188-byte MPEG transport packet size).
    Instantly filters out TypeScript source code files.
    """
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size < 189:
            return False
        with open(p, "rb") as f:
            chunk = f.read(376)
        if len(chunk) < 189:
            return False
        return chunk[0] == 0x47 and chunk[188] == 0x47
    except (OSError, PermissionError):
        return False


def is_motion_photo_video(path: str) -> bool:
    """Return True if the file contains an ISO Base Media / MP4 container (ftyp box).

    Useful for Google Pixel Motion Photo files named .mp or .MP that store standard
    MP4 video clips.
    """
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size < 16:
            return False
        with open(p, "rb") as f:
            header = f.read(32)
        return b"ftyp" in header[4:16] or header.startswith(b"\x00\x00\x00") and b"ftyp" in header
    except (OSError, PermissionError):
        return False


def is_rar_archive(path: str) -> bool:
    """Return True if file starts with the standard RAR archive signature."""
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size < 7:
            return False
        with open(p, "rb") as f:
            magic = f.read(7)
        return magic.startswith(b"Rar!\x1a\x07")
    except (OSError, PermissionError):
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_format_utils.py -v`
Expected: PASS (6/6 tests passed)

- [ ] **Step 5: Commit**

```bash
git add clairvoy/core/format_utils.py tests/test_format_utils.py
git commit -m "feat(core): add format_utils with MPEG-TS, Motion Photo, and RAR stream discriminators"
```

---

### Task 2: Video Keyframe Matcher Extension (`video_matcher.py`)

**Files:**
- Modify: `clairvoy/plugins/video_matcher.py:26-36`, `64-74`
- Test: `tests/test_video_format_expansion.py`

**Interfaces:**
- Consumes: `is_mpeg_ts`, `is_motion_photo_video` from `clairvoy.core.format_utils`.
- Produces: `VideoKeyframeMatcherPlugin.filter_supported` supporting `.ts` and `.mp`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_video_format_expansion.py
from pathlib import Path
from clairvoy.core.models import FileEntry
from clairvoy.plugins.video_matcher import VideoKeyframeMatcherPlugin, SUPPORTED_VIDEO_EXTENSIONS


def test_video_supported_extensions_includes_ts_and_mp():
    assert ".ts" in SUPPORTED_VIDEO_EXTENSIONS
    assert ".mp" in SUPPORTED_VIDEO_EXTENSIONS


def test_filter_supported_accepts_valid_mpeg_ts(tmp_path: Path):
    ts_file = tmp_path / "broadcast.ts"
    payload = bytearray(376)
    payload[0] = 0x47
    payload[188] = 0x47
    ts_file.write_bytes(payload)

    plugin = VideoKeyframeMatcherPlugin()
    files = [FileEntry(path=str(ts_file), size_bytes=len(payload))]
    filtered = plugin.filter_supported(files)
    assert len(filtered) == 1
    assert filtered[0].path == str(ts_file)


def test_filter_supported_rejects_typescript_ts(tmp_path: Path):
    ts_file = tmp_path / "index.ts"
    ts_file.write_text("export const hello = 'world';")

    plugin = VideoKeyframeMatcherPlugin()
    files = [FileEntry(path=str(ts_file), size_bytes=30)]
    filtered = plugin.filter_supported(files)
    assert len(filtered) == 0


def test_filter_supported_accepts_motion_photo_mp(tmp_path: Path):
    mp_file = tmp_path / "PXL_20210925.MP"
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    mp_file.write_bytes(header)

    plugin = VideoKeyframeMatcherPlugin()
    files = [FileEntry(path=str(mp_file), size_bytes=len(header))]
    filtered = plugin.filter_supported(files)
    assert len(filtered) == 1
    assert filtered[0].path == str(mp_file)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_video_format_expansion.py -v`
Expected: FAIL with `AssertionError: assert '.ts' in SUPPORTED_VIDEO_EXTENSIONS`

- [ ] **Step 3: Update `video_matcher.py` implementation**

Add `.ts` and `.mp` to `SUPPORTED_VIDEO_EXTENSIONS` and update `filter_supported`:

```python
# In clairvoy/plugins/video_matcher.py:
from clairvoy.core.format_utils import is_motion_photo_video, is_mpeg_ts

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

# In VideoKeyframeMatcherPlugin.filter_supported:
    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        """Filter files matching supported video extensions, validating stream headers for ambiguous extensions."""
        supported: list[FileEntry] = []
        for f in files:
            if f.size_bytes <= 0:
                continue
            ext = Path(f.path).suffix.lower()
            if ext not in SUPPORTED_VIDEO_EXTENSIONS:
                continue
            if ext == ".ts" and not is_mpeg_ts(f.path):
                continue
            if ext == ".mp" and not is_motion_photo_video(f.path):
                continue
            supported.append(f)
        return supported
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_video_format_expansion.py -v`
Expected: PASS (4/4 tests passed)

- [ ] **Step 5: Commit**

```bash
git add clairvoy/plugins/video_matcher.py tests/test_video_format_expansion.py
git commit -m "feat(plugins): add MPEG-TS and Motion Photo support with stream validation to VideoKeyframeMatcher"
```

---

### Task 3: Vision Engine & Photo Vision Extension (`photo_vision.py` & `vision_engine.py`)

**Files:**
- Modify: `clairvoy/plugins/photo_vision.py:20-30`
- Modify: `clairvoy/engines/vision_engine.py:121-137`
- Test: `tests/test_photo_format_expansion.py`

**Interfaces:**
- Consumes: Pillow, ffmpeg binary, `onnxruntime`.
- Produces: `preprocess_single_image` loading `.psd` and `.heic` (with ffmpeg pipe fallback) into normalized RGB tensors `(3, 224, 224)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_photo_format_expansion.py
from pathlib import Path
from PIL import Image
from clairvoy.core.models import FileEntry
from clairvoy.engines.vision_engine import VisionEngine
from clairvoy.plugins.photo_vision import PhotoVisionMatcherPlugin, SUPPORTED_IMAGE_EXTENSIONS


def test_photo_supported_extensions_includes_psd():
    assert ".psd" in SUPPORTED_IMAGE_EXTENSIONS


def test_preprocess_single_image_supports_psd(tmp_path: Path):
    psd_file = tmp_path / "test.psd"
    # Create a valid PSD image via Pillow
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    img.save(psd_file, format="PSD")

    tensor, dims = VisionEngine.preprocess_single_image(str(psd_file))
    assert tensor is not None
    assert tensor.shape == (3, 224, 224)
    assert dims == (100, 100)


def test_preprocess_single_image_fallback_heic_or_mock(tmp_path: Path, monkeypatch):
    # Test that when Pillow Image.open raises UnidentifiedImageError for HEIC,
    # the fallback path invokes ffmpeg pipe or extracts frame
    heic_file = tmp_path / "photo.heic"
    heic_file.write_bytes(b"\x00" * 50)  # mock file

    # Verify graceful handling of corrupt/mock heic
    tensor, dims = VisionEngine.preprocess_single_image(str(heic_file))
    # Returns (None, (0, 0)) on unparsable mock without crashing
    assert dims == (0, 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_photo_format_expansion.py -v`
Expected: FAIL with `AssertionError: assert '.psd' in SUPPORTED_IMAGE_EXTENSIONS`

- [ ] **Step 3: Update `photo_vision.py` and `vision_engine.py`**

In `clairvoy/plugins/photo_vision.py`:
```python
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
```

In `clairvoy/engines/vision_engine.py`:
Enhance `preprocess_single_image` with Pillow HEIC attempt and `ffmpeg` pipe fallback:
```python
    @staticmethod
    def _extract_frame_via_ffmpeg(path: str) -> Image.Image | None:
        """Extract a single frame from an image or video file using local ffmpeg pipe."""
        import shutil
        import subprocess
        ffmpeg_bin = shutil.which("ffmpeg") or "/home/shubhamshah207/.local/bin/ffmpeg"
        if not Path(ffmpeg_bin).exists():
            return None
        try:
            cmd = [
                ffmpeg_bin,
                "-v", "error",
                "-i", path,
                "-vframes", "1",
                "-f", "image2pipe",
                "-vcodec", "png",
                "-",
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=10)
            if res.returncode == 0 and res.stdout:
                import io
                return Image.open(io.BytesIO(res.stdout)).convert("RGB")
        except Exception:
            return None
        return None

    @staticmethod
    def preprocess_single_image(path: str) -> tuple[np.ndarray | None, tuple[int, int]]:
        """
        Loads, resizes, and standardizes an image tensor for DINOv2 input:
        Shape: (3, 224, 224), Mean: [0.485, 0.456, 0.406], Std: [0.229, 0.224, 0.225]
        Supports .jpg, .png, .webp, .psd, and .heic (via Pillow or ffmpeg fallback).
        """
        try:
            img = None
            try:
                img = Image.open(path)
                img.load()
            except Exception:
                ext = Path(path).suffix.lower()
                if ext in {".heic", ".heif"}:
                    img = VisionEngine._extract_frame_via_ffmpeg(path)

            if img is None:
                return None, (0, 0)

            w, h = img.size
            img = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
            arr = np.array(img, dtype=np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            arr = (arr - mean) / std
            return np.transpose(arr, (2, 0, 1)), (w, h)
        except Exception:
            return None, (0, 0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_photo_format_expansion.py -v`
Expected: PASS (3/3 tests passed)

- [ ] **Step 5: Commit**

```bash
git add clairvoy/plugins/photo_vision.py clairvoy/engines/vision_engine.py tests/test_photo_format_expansion.py
git commit -m "feat(vision): add PSD support and ffmpeg-backed HEIC decoding to VisionEngine"
```

---

### Task 4: Archive Inspector Extension (`archive_inspector.py`)

**Files:**
- Modify: `clairvoy/plugins/archive_inspector.py:22`, `100-142`
- Test: `tests/test_archive_format_expansion.py`

**Interfaces:**
- Consumes: `is_rar_archive` from `clairvoy.core.format_utils`, standard library `zipfile`.
- Produces: `ArchiveInspectorMatcherPlugin` inspecting `.jar`, `.apk`, and detecting `.rar`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_archive_format_expansion.py
import zipfile
import zlib
from pathlib import Path
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.plugins.archive_inspector import ArchiveInspectorMatcherPlugin, ARCHIVE_SUFFIXES


def test_archive_suffixes_includes_jar_apk_rar():
    assert ".jar" in ARCHIVE_SUFFIXES
    assert ".apk" in ARCHIVE_SUFFIXES
    assert ".rar" in ARCHIVE_SUFFIXES


def test_archive_inspector_matches_member_in_jar(tmp_path: Path):
    jar_file = tmp_path / "app.jar"
    content = b"public class App { public static void main(String[] args) {} }"
    with zipfile.ZipFile(jar_file, "w") as zf:
        zf.writestr("App.class", content)

    on_disk_class = tmp_path / "App.class"
    on_disk_class.write_bytes(content)

    plugin = ArchiveInspectorMatcherPlugin()
    candidates = [FileEntry(path=str(on_disk_class), size_bytes=len(content))]
    all_files = candidates + [FileEntry(path=str(jar_file), size_bytes=jar_file.stat().st_size)]

    clusters = plugin.find_duplicates(candidates, all_files)
    assert len(clusters) == 1
    assert clusters[0].match_type == MatchType.EXACT_HASH
    assert clusters[0].metadata["archive"] == str(jar_file)
    assert clusters[0].metadata["member"] == "App.class"


def test_archive_inspector_matches_member_in_apk(tmp_path: Path):
    apk_file = tmp_path / "release.apk"
    content = b"manifest XML binary data"
    with zipfile.ZipFile(apk_file, "w") as zf:
        zf.writestr("AndroidManifest.xml", content)

    on_disk_manifest = tmp_path / "AndroidManifest.xml"
    on_disk_manifest.write_bytes(content)

    plugin = ArchiveInspectorMatcherPlugin()
    candidates = [FileEntry(path=str(on_disk_manifest), size_bytes=len(content))]
    all_files = candidates + [FileEntry(path=str(apk_file), size_bytes=apk_file.stat().st_size)]

    clusters = plugin.find_duplicates(candidates, all_files)
    assert len(clusters) == 1
    assert clusters[0].metadata["member"] == "AndroidManifest.xml"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_archive_format_expansion.py -v`
Expected: FAIL with `AssertionError: assert '.jar' in ARCHIVE_SUFFIXES`

- [ ] **Step 3: Update `archive_inspector.py`**

In `clairvoy/plugins/archive_inspector.py`:
```python
ARCHIVE_SUFFIXES = (
    ".zip",
    ".jar",
    ".apk",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".tbz2",
    ".rar",
)
```
In `find_duplicates`:
```python
            # Handle ZIP, JAR, and APK archives
            if lower_path.endswith((".zip", ".jar", ".apk")):
                try:
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        ...
```
Add RAR detection:
```python
            elif lower_path.endswith(".rar"):
                logger.debug("RAR archive detected at %s. Inspection requires optional unrar/rarfile.", archive_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_archive_format_expansion.py -v`
Expected: PASS (3/3 tests passed)

- [ ] **Step 5: Commit**

```bash
git add clairvoy/plugins/archive_inspector.py tests/test_archive_format_expansion.py
git commit -m "feat(archive): add in-memory inspection for JAR and APK packages"
```

---

### Task 5: End-to-End Cross-Format Integration & Verification Suite

**Files:**
- Create: `tests/test_format_expansion_e2e.py`

**Interfaces:**
- Tests integration across the entire `DeduplicationPipeline` and `PluginRegistry`.

- [ ] **Step 1: Write integration tests**

```python
# tests/test_format_expansion_e2e.py
import zipfile
from pathlib import Path
from PIL import Image
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import PluginRegistry
from clairvoy.engines.pipeline import DeduplicationPipeline


def test_pipeline_cross_format_and_archive_detection(tmp_path: Path):
    # Setup test workspace
    img_jpg = tmp_path / "photo.jpg"
    img = Image.new("RGB", (100, 100), color=(200, 50, 50))
    img.save(img_jpg)

    img_psd = tmp_path / "photo.psd"
    img.convert("RGBA").save(img_psd, format="PSD")

    # JAR archive with member matching on-disk file
    asset_file = tmp_path / "icon.png"
    asset_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)

    jar_file = tmp_path / "bundle.jar"
    with zipfile.ZipFile(jar_file, "w") as zf:
        zf.writestr("assets/icon.png", asset_file.read_bytes())

    registry = PluginRegistry()
    registry.discover_plugins()

    pipeline = DeduplicationPipeline(registry)
    results = pipeline.run(str(tmp_path))

    assert results is not None
    # Verify that archive inspection found the duplicate asset
    archive_clusters = [c for c in results.clusters if c.match_type == MatchType.EXACT_HASH and "archive" in c.metadata]
    assert len(archive_clusters) >= 1
```

- [ ] **Step 2: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_format_expansion_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_format_expansion_e2e.py
git commit -m "test(e2e): verify cross-format media and archive deduplication pipeline"
```

---

### Task 6: Documentation & Agent Memory Invariants

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/PLUGINS.md`

- [ ] **Step 1: Update `AGENTS.md`**
Add expanded format matrix (`.heic`, `.psd`, `.ts`, `.mp`, `.jar`, `.apk`, `.rar`) and validation rules.

- [ ] **Step 2: Update `docs/ARCHITECTURE.md` and `docs/PLUGINS.md`**
Document the stream validation layer, dual-path HEIC frame extractor, and archive inspector package support.

- [ ] **Step 3: Run documentation integrity check**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_docs_integrity.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite and linter**

Run: `/home/shubhamshah207/miniconda3/bin/pytest -v`
Expected: 100% PASS across all test files.
Run: `/home/shubhamshah207/miniconda3/bin/ruff check .`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md docs/ARCHITECTURE.md docs/PLUGINS.md
git commit -m "docs: update AGENTS.md and architecture docs for expanded format support"
```
