# Clairvoy Architecture & Deep Modules Blueprint

This document details the internal architecture, module boundaries, and data pipelines of Clairvoy.
Refer to this document for architectural patterns and deep module design.

---

## 1. System Architecture

Clairvoy follows the **Deep Module** philosophy (*A Philosophy of Software Design*): complex operations are encapsulated behind simple, cohesive, and type-safe public interfaces.

```
+---------------------------------------------------------------------------------+
|                                 CLAIRVOY ENGINE                                 |
+---------------------------------------------------------------------------------+
|                                                                                 |
|   +-------------------+      +---------------------+      +-----------------+   |
|   |    CLI (Typer)    |      |    FastAPI (Web)    |      | Custom Plugins  |   |
|   |  clairvoy/cli.py  |      |   clairvoy/web/     |      | ~/.clairvoy/... |   |
|   +---------+---------+      +----------+----------+      +--------+--------+   |
|             |                           |                          |            |
|             +---------------------+     |     +--------------------+            |
|                                   v     v     v                                 |
|                        +---------------------------+                            |
|                        |       PluginRegistry      |                            |
|                        | clairvoy/core/plugins.py  |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|                                      v                                          |
|                        +---------------------------+                            |
|                        |   DeduplicationPipeline   |                            |
|                        | clairvoy/engines/pipeline |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|         +----------------------------+----------------------------+             |
|         |                            |                            |             |
|         v                            v                            v             |
|  [Tier 1 Matchers]          [Tier 2 Matchers]            [Tier 3 Matchers]      |
|  ExactHashMatcherPlugin     PhotoVisionMatcherPlugin     ArchiveInspector...    |
|  (QuickHash + SHA-256)      (DINOv2 Embeddings)          (ZIP/TAR in-memory)    |
|         |                            |                            |             |
|         +----------------------------+----------------------------+             |
|                                      |                                          |
|                                      v                                          |
|                        +---------------------------+                            |
|                        |  CompositeKeeperStrategy  |                            |
|                        |  (Scoring & Seniority)    |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|                                      v                                          |
|         +----------------------------+----------------------------+             |
|         |                                                         |             |
|         v                                                         v             |
|  [Action: SafeQuarantine]                                  [Action: Hardlink]   |
|  SafeQuarantineActionPlugin                                HardlinkActionPlugin |
+---------------------------------------------------------------------------------+
```

---

## 2. Deep Module Organization

The codebase is strictly structured into 4 cohesive packages with minimal cross-talk:

### `clairvoy.core` (Data Domain, Security, Contracts)
- [`models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py): Canonical Pydantic v2 schemas (`FileEntry`, `DuplicateRecord`, `DuplicateCluster`, `ScanSummary`, `ActionResult`).
- [`format_utils.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/format_utils.py): $O(1)$ stream header validators (`is_mpeg_ts`, `is_motion_photo_video`, `is_rar_archive`) discriminating media streams from ambiguous source files.
- [`plugins.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py): Base plugin ABCs (`BasePlugin`, `BaseMatcherPlugin`, `BaseKeeperPlugin`, `BaseActionPlugin`) and thread-safe `PluginRegistry`.
- [`security.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/security.py): Enterprise filesystem defenses: path traversal verification, system root protection, sanitized shell command generation.
- [`config.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/config.py): Global configuration defaults and environment variable overrides.

### `clairvoy.engines` (Computation, Inference, Orchestration)
- [`pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py): `DeduplicationPipeline` coordinating chained matchers with short-circuit pruning, plus `CompositeKeeperStrategy`.
- [`storage_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/storage_engine.py): Multi-threaded filesystem scanner, 128KB head/tail QuickHash, and SHA-256 digests.
- [`vision_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/vision_engine.py): 100% offline Meta DINOv2 ONNX Runtime embedding inference, dual-path HEIC frame decoding, and Disjoint Set Union (DSU) graph clustering.
- [`classifier_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/classifier_engine.py): Fast cosine distance classifier categorizing media into Photo, Screenshot, Meme, or Document.
- [`quarantine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/quarantine.py): Manifest-backed non-destructive quarantine isolation engine with automated rollback generator.

### `clairvoy.plugins` (Bundled Default Extensions)
- [`exact_hash.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/exact_hash.py): Tier 1 byte-for-byte deduplication (Priority 10).
- [`photo_vision.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py): Tier 2 visual similarity deduplication supporting `.jpg`, `.png`, `.webp`, `.heic`, and `.psd` (Priority 20).
- [`video_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py): Tier 3 video keyframe hash deduplication supporting `.mp4`, `.mkv`, `.mov`, `.ts`, and `.mp` (Priority 30).
- [`archive_inspector.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py): Tier 4 in-memory ZIP/TAR/JAR/APK central directory inspector (Priority 40).
- [`quarantine_action.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/quarantine_action.py): Safe reversible quarantine action.
- [`hardlink_action.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/hardlink_action.py): Cross-filesystem safe hardlink replacement action.

### `clairvoy.cli` & `clairvoy.web` (Presentation & Interfaces)
- [`cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py): Typer CLI with `scan`, `review`, `quarantine`, `restore`, `plugins list`, and `plugins info`.
- [`web/app.py`](file:///home/shubhamshah207/clairvoy/clairvoy/web/app.py): FastAPI backend serving interactive UI for side-by-side visual diffs and manual reviews.

---

## 3. Chained Pipeline & Short-Circuit Pruning

To maximize speed and minimize compute, matchers run strictly in ascending computational cost order:

```
[Candidate Files]
       |
       v
+-------------------------------+
| Tier 1: ExactHashMatcher     | (Cost: Low - 128KB QuickHash + SHA-256)
+---------------+---------------+
                |
                +---> [Exact Duplicates Found] ---> Removed from downstream pipeline
                |
                v
+-------------------------------+
| Tier 2: PhotoVisionMatcher   | (Cost: Medium - Local ONNX DINOv2)
+---------------+---------------+
                |
                +---> [Visual Duplicates Found] ---> Removed from downstream pipeline
                |
                v
+-------------------------------+
| Tier 3: VideoKeyframeMatcher | (Cost: High - PyAV keyframe extraction)
+---------------+---------------+
                |
                +---> [Video Duplicates Found]  ---> Removed from downstream pipeline
                |
                v
+-------------------------------+
| Tier 4: ArchiveInspector      | (Cost: Medium - In-memory ZIP/TAR parse)
+---------------+---------------+
                |
                v
       [Combined Clusters]
```

### Short-Circuit Pruning Guarantee
Once a file is identified as a member of a duplicate cluster in an earlier tier, it is **pruned from the candidate pool** for all subsequent tiers. This prevents expensive neural embedding inference or video frame decoding on files that are already proven exact duplicates.

---

## 4. Keeper Resolution & Scoring Engine

When duplicate clusters are identified, `CompositeKeeperStrategy` determines which file to keep (`ActionType.KEEP`) and which to flag as duplicates (`ActionType.DUPLICATE`).

### Scoring Criteria:
1. **Resolution & Media Dimensions**: Higher resolution receives higher score.
2. **File Size & Bitrate**: Higher information density receives bonus.
3. **Duplicate Token Penalties**: Filenames containing `copy`, `(1)`, `_1`, `dupe`, or trailing numeric suffixes receive severe penalties.
4. **Directory Seniority / Clean Path Bonus**: Shorter, cleaner directory paths receive preference over deeply nested temp folders.
5. **Modification Time Tie-Breaking**: When scores are identical, the oldest original file is preserved.
