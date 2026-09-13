# Pluggable Deduplication Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully pluggable, extensible deduplication engine for Clairvoy adhering to Pipeline, Strategy, Registry, Template Method, and Observer design patterns, bundling 6 core default plugins (Exact Hash, Photo Vision, Video Keyframe Matcher, Archive Inspector, Safe Quarantine, NTFS/Linux Hardlink) and supporting dynamic custom plugin loading from `~/.clairvoy/plugins/`.

**Architecture:** A centralized `PluginRegistry` dynamically discovers and validates `BaseMatcherPlugin` (Pipeline / Chain of Responsibility), `BaseKeeperPlugin` (Strategy), and `BaseActionPlugin` (Strategy). Files pass through tiered matchers in order of computational cost, and duplicates are resolved safely with non-clobbering quarantine or zero-space hardlinks.

**Tech Stack:** Python 3.12, Pydantic v2, ONNX Runtime, NumPy, Pillow, Pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-09-13-pluggable-engine-design.md`

## Global Constraints
- All diagrams displayed in terminal/chat must be ASCII text art.
- All file links must use clickable `file://` markdown scheme.
- 100% offline, local-first execution (no cloud API dependencies required).
- Strict type hints with Python 3.12 syntax (`type | None`, `list[T]`).
- Zero-clobber non-destructive operations with rollback logging.
- `ruff check .` and `pytest` must pass at 100% after every task.

---

### Task 1: Core Plugin Interfaces & Dynamic Registry

**Files:**
- Create: `clairvoy/core/plugins.py`
- Test: `tests/test_plugin_system.py`

**Interfaces:**
- Produces:
  - `BasePlugin`: Base abstract class with `plugin_id`, `display_name`, `is_available()`, `initialize()`, `shutdown()`.
  - `BaseMatcherPlugin(BasePlugin)`: Abstract matcher with `match_type`, `priority_order`, `filter_supported()`, `find_duplicates()`.
  - `BaseKeeperPlugin(BasePlugin)`: Abstract keeper strategy with `score_entry()`.
  - `BaseActionPlugin(BasePlugin)`: Abstract resolution action with `execute()`.
  - `PluginRegistry`: Thread-safe registry with `register()`, `get_matchers()`, `get_keepers()`, `get_action()`, `load_plugins_from_directory()`, `load_entry_points()`.
  - `DuplicateCluster`: Pydantic model for discovered duplicate clusters.

- [ ] **Step 1: Write the failing test for plugin registration and lifecycle**

```python
# tests/test_plugin_system.py
from pathlib import Path
from clairvoy.core.models import MatchType
from clairvoy.core.plugins import (
    BaseActionPlugin,
    BaseKeeperPlugin,
    BaseMatcherPlugin,
    DuplicateCluster,
    PluginRegistry,
)


class DummyMatcher(BaseMatcherPlugin):
    plugin_id = "dummy_matcher"
    display_name = "Dummy Matcher"
    match_type = MatchType.EXACT_HASH
    priority_order = 50

    def is_available(self) -> tuple[bool, str]:
        return True, "Ready"

    def filter_supported(self, files):
        return files

    def find_duplicates(self, candidates, all_indexed_files, context):
        return []


def test_plugin_registry_registration():
    registry = PluginRegistry()
    matcher = DummyMatcher()
    registry.register(matcher)

    assert "dummy_matcher" in registry.list_plugin_ids()
    matchers = registry.get_matchers()
    assert len(matchers) == 1
    assert matchers[0].plugin_id == "dummy_matcher"


def test_dynamic_plugin_loader_from_dir(temp_workspace):
    plugin_dir = temp_workspace / "plugins"
    plugin_dir.mkdir()
    plugin_file = plugin_dir / "custom_keeper.py"
    plugin_file.write_text(
        """
from clairvoy.core.plugins import BaseKeeperPlugin

class CustomKeeper(BaseKeeperPlugin):
    plugin_id = "custom_keeper"
    display_name = "Custom Keeper"

    def is_available(self):
        return True, "Ready"

    def score_entry(self, entry, cluster):
        return 999
"""
    )

    registry = PluginRegistry()
    loaded = registry.load_plugins_from_directory(plugin_dir)
    assert len(loaded) == 1
    assert "custom_keeper" in registry.list_plugin_ids()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_plugin_system.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clairvoy.core.plugins'`

- [ ] **Step 3: Implement `clairvoy/core/plugins.py`**

Implement `BasePlugin`, `BaseMatcherPlugin`, `BaseKeeperPlugin`, `BaseActionPlugin`, `DuplicateCluster`, and `PluginRegistry` supporting dynamic discovery via `importlib.util.spec_from_file_location` and entry points.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_plugin_system.py -v`
Expected: PASS

- [ ] **Step 5: Lint and Commit**

```bash
/home/shubhamshah207/miniconda3/bin/ruff check .
git add clairvoy/core/plugins.py tests/test_plugin_system.py
git commit -m "feat(plugins): implement core plugin interfaces and dynamic registry"
```

---

### Task 2: Exact Hash Matcher & Archive Inspector Plugins

**Files:**
- Create: `clairvoy/plugins/__init__.py`
- Create: `clairvoy/plugins/exact_hash.py`
- Create: `clairvoy/plugins/archive_inspector.py`
- Test: `tests/test_matcher_plugins.py`

**Interfaces:**
- Consumes: `BaseMatcherPlugin`, `DuplicateCluster`, `FileEntry` from `clairvoy.core.plugins`
- Produces:
  - `ExactHashMatcherPlugin`: Encapsulates Size grouping + 128KB QuickHash + SHA-256 (`priority_order = 10`).
  - `ArchiveInspectorMatcherPlugin`: In-memory inspection of `.zip` and `.tar` archives without extraction, matching on-disk files with archive contents (`priority_order = 40`).

- [ ] **Step 1: Write the failing tests for ExactHashMatcher and ArchiveInspector**

```python
# tests/test_matcher_plugins.py
import zipfile
from pathlib import Path
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin
from clairvoy.plugins.archive_inspector import ArchiveInspectorMatcherPlugin


def test_exact_hash_matcher(temp_workspace):
    f1 = temp_workspace / "file1.txt"
    f2 = temp_workspace / "file2.txt"
    f3 = temp_workspace / "unique.txt"
    f1.write_text("duplicate content 123456789")
    f2.write_text("duplicate content 123456789")
    f3.write_text("unique content 987654321")

    entries = [
        FileEntry(path=str(f1), size_bytes=f1.stat().st_size),
        FileEntry(path=str(f2), size_bytes=f2.stat().st_size),
        FileEntry(path=str(f3), size_bytes=f3.stat().st_size),
    ]

    matcher = ExactHashMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={})

    assert len(clusters) == 1
    assert len(clusters[0].members) == 2
    paths = {m.path for m in clusters[0].members}
    assert str(f1) in paths and str(f2) in paths


def test_archive_inspector_matcher(temp_workspace):
    # Create an on-disk file
    doc = temp_workspace / "invoice.pdf"
    doc_content = b"PDF invoice content for client XYZ"
    doc.write_bytes(doc_content)

    # Create a zip containing the identical file
    zip_path = temp_workspace / "backup.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("invoices/invoice.pdf", doc_content)

    entries = [
        FileEntry(path=str(doc), size_bytes=len(doc_content)),
        FileEntry(path=str(zip_path), size_bytes=zip_path.stat().st_size),
    ]

    matcher = ArchiveInspectorMatcherPlugin()
    clusters = matcher.find_duplicates(entries, entries, context={})
    assert len(clusters) == 1
    assert "invoice.pdf" in clusters[0].members[0].path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_matcher_plugins.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clairvoy.plugins'`

- [ ] **Step 3: Implement `clairvoy/plugins/exact_hash.py` and `clairvoy/plugins/archive_inspector.py`**

Implement parallel QuickHash + SHA-256 in `ExactHashMatcherPlugin`.
Implement in-memory ZIP central directory CRC32/size lookup in `ArchiveInspectorMatcherPlugin`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_matcher_plugins.py -v`
Expected: PASS

- [ ] **Step 5: Lint and Commit**

```bash
/home/shubhamshah207/miniconda3/bin/ruff check .
git add clairvoy/plugins/__init__.py clairvoy/plugins/exact_hash.py clairvoy/plugins/archive_inspector.py tests/test_matcher_plugins.py
git commit -m "feat(plugins): implement exact hash matcher and archive inspector plugins"
```

---

### Task 3: Photo Vision & Video Keyframe Matcher Plugins

**Files:**
- Create: `clairvoy/plugins/photo_vision.py`
- Create: `clairvoy/plugins/video_matcher.py`
- Test: `tests/test_media_matchers.py`

**Interfaces:**
- Consumes: `BaseMatcherPlugin`, `VisionEngine`, `FileEntry`
- Produces:
  - `PhotoVisionMatcherPlugin`: Meta DINOv2 visual similarity clustering (`priority_order = 20`).
  - `VideoKeyframeMatcherPlugin`: Container duration match (±1.5%) + keyframe thumbnail similarity for transcode matching (`priority_order = 30`).

- [ ] **Step 1: Write the failing tests for media matcher plugins**

```python
# tests/test_media_matchers.py
from PIL import Image
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.plugins.photo_vision import PhotoVisionMatcherPlugin
from clairvoy.plugins.video_matcher import VideoKeyframeMatcherPlugin


def test_photo_vision_matcher_plugin(temp_workspace):
    p1 = temp_workspace / "photo_a.jpg"
    p2 = temp_workspace / "photo_b.jpg"
    img = Image.new("RGB", (300, 300), color=(100, 150, 200))
    img.save(p1)
    img.save(p2)

    entries = [
        FileEntry(path=str(p1), size_bytes=p1.stat().st_size, is_media=True),
        FileEntry(path=str(p2), size_bytes=p2.stat().st_size, is_media=True),
    ]

    plugin = PhotoVisionMatcherPlugin()
    avail, _ = plugin.is_available()
    if avail:
        clusters = plugin.find_duplicates(entries, entries, context={"threshold": 0.90})
        assert len(clusters) == 1
        assert len(clusters[0].members) == 2


def test_video_matcher_availability():
    plugin = VideoKeyframeMatcherPlugin()
    avail, reason = plugin.is_available()
    assert isinstance(avail, bool)
    assert isinstance(reason, str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_media_matchers.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `clairvoy/plugins/photo_vision.py` and `clairvoy/plugins/video_matcher.py`**

Encapsulate DINOv2 vision clustering in `PhotoVisionMatcherPlugin`.
Implement `VideoKeyframeMatcherPlugin` with stream duration extraction and frame sampling with graceful degradation.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_media_matchers.py -v`
Expected: PASS

- [ ] **Step 5: Lint and Commit**

```bash
/home/shubhamshah207/miniconda3/bin/ruff check .
git add clairvoy/plugins/photo_vision.py clairvoy/plugins/video_matcher.py tests/test_media_matchers.py
git commit -m "feat(plugins): implement photo vision and video keyframe matcher plugins"
```

---

### Task 4: Action Plugins (Safe Quarantine & NTFS Hardlink)

**Files:**
- Create: `clairvoy/plugins/quarantine_action.py`
- Create: `clairvoy/plugins/hardlink_action.py`
- Test: `tests/test_action_plugins.py`

**Interfaces:**
- Consumes: `BaseActionPlugin`, `QuarantineEngine`, `DuplicateRecord`
- Produces:
  - `SafeQuarantineActionPlugin`: Reversible isolation with non-clobbering and rollback manifest.
  - `HardlinkActionPlugin`: Zero-space deduplication replacing duplicates with hardlinks.

- [ ] **Step 1: Write the failing tests for action plugins**

```python
# tests/test_action_plugins.py
from pathlib import Path
from clairvoy.core.models import ActionType, DuplicateRecord, ImageCategory, MatchType
from clairvoy.plugins.hardlink_action import HardlinkActionPlugin
from clairvoy.plugins.quarantine_action import SafeQuarantineActionPlugin


def test_hardlink_action(temp_workspace):
    keeper = temp_workspace / "keeper.jpg"
    dupe = temp_workspace / "dupe.jpg"
    keeper.write_text("sample media payload")
    dupe.write_text("sample media payload")

    records = [
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.PHOTO,
        ),
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.DUPLICATE,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(dupe),
            category=ImageCategory.PHOTO,
        ),
    ]

    action = HardlinkActionPlugin()
    result = action.execute(records, base_dirs=[temp_workspace])
    assert result.success_count == 1

    # Verify same inode
    assert keeper.stat().st_ino == dupe.stat().st_ino
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_action_plugins.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `clairvoy/plugins/quarantine_action.py` and `clairvoy/plugins/hardlink_action.py`**

Implement quarantine with manifest rollback.
Implement hardlinking with cross-filesystem partition error handling.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_action_plugins.py -v`
Expected: PASS

- [ ] **Step 5: Lint and Commit**

```bash
/home/shubhamshah207/miniconda3/bin/ruff check .
git add clairvoy/plugins/quarantine_action.py clairvoy/plugins/hardlink_action.py tests/test_action_plugins.py
git commit -m "feat(plugins): implement quarantine and hardlink action plugins"
```

---

### Task 5: Pipeline Orchestrator Engine & Keeper Strategies

**Files:**
- Create: `clairvoy/engines/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `PluginRegistry`, `StorageEngine`, `FileEntry`
- Produces:
  - `DeduplicationPipeline`: Coordinates scanner $\rightarrow$ chained matchers $\rightarrow$ keeper scorer $\rightarrow$ summary generation.
  - `CompositeKeeperStrategy`: Combines metadata, quality, and directory seniority.

- [ ] **Step 1: Write the failing tests for DeduplicationPipeline**

```python
# tests/test_pipeline.py
from clairvoy.core.plugins import PluginRegistry
from clairvoy.engines.pipeline import DeduplicationPipeline
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin
from clairvoy.plugins.quarantine_action import SafeQuarantineActionPlugin


def test_pipeline_end_to_end(sample_dataset):
    root = sample_dataset["root"]
    registry = PluginRegistry()
    registry.register(ExactHashMatcherPlugin())
    registry.register(SafeQuarantineActionPlugin())

    pipeline = DeduplicationPipeline(paths=[root], registry=registry)
    summary = pipeline.run_scan()

    assert summary.total_files_scanned >= 3
    assert summary.exact_duplicate_groups == 1
    assert summary.total_duplicate_groups == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clairvoy.engines.pipeline'`

- [ ] **Step 3: Implement `clairvoy/engines/pipeline.py`**

Implement pipeline chaining matchers in priority order, removing matched paths from downstream matchers to minimize compute. Integrate observer progress reporting.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Lint and Commit**

```bash
/home/shubhamshah207/miniconda3/bin/ruff check .
git add clairvoy/engines/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): implement deduplication pipeline orchestrator"
```

---

### Task 6: CLI Plugins Command & End-to-End System Verification

**Files:**
- Modify: `clairvoy/cli.py`
- Test: `tests/test_cli_plugins.py`

**Interfaces:**
- Exposes:
  - `clairvoy plugins list`: Shows all discovered plugins, versions, status, and whether enabled.
  - `clairvoy scan --plugin ... --action hardlink`: Allows toggling plugins and selecting resolution actions from the CLI.

- [ ] **Step 1: Write the failing test for CLI plugin commands**

```python
# tests/test_cli_plugins.py
from typer.testing import CliRunner
from clairvoy.cli import main_app_or_parser # Adjust to CLI structure

def test_cli_plugins_list():
    # Verify clairvoy plugins list prints default plugins
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_cli_plugins.py -v`
Expected: FAIL

- [ ] **Step 3: Implement CLI plugin subcommands and scan flags in `clairvoy/cli.py`**

Add `plugins` command group: `list`, `info`. Add `--enable-plugin`, `--disable-plugin`, `--action` flags to `scan`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_cli_plugins.py -v`
Expected: PASS

- [ ] **Step 5: Full regression verification**

Run: `/home/shubhamshah207/miniconda3/bin/pytest && /home/shubhamshah207/miniconda3/bin/ruff check .`
Expected: 100% PASS on all tests with 0 ruff errors.

- [ ] **Step 6: Commit and Push**

```bash
git add clairvoy/cli.py tests/test_cli_plugins.py
git commit -m "feat(cli): add plugin management commands and scan action flags"
git push origin main
```
