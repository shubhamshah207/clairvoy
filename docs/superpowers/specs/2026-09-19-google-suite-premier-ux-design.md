# Google Suite Premier UX Specification: Clairvoy Multimodal Storage Studio

**Author:** Senior Product Manager, Storage & Media Platforms (Google Design System)  
**Target Platform:** Pure Rust Axum Web Service (`crates/clairvoy-server/src/index.html`)  
**Design Standard:** Google Material Design 3 (M3) + Google Photos + Google Drive + Google One + Files by Google  
**Date:** September 19, 2026  
**Status:** Approved Product Specification

---

## 1. Executive Strategy & Target Audience

Clairvoy solves a universal human problem: **storage exhaustion and duplicate media chaos**.
As Senior Product Management across Google Photos, Google Drive, Google One, and Files by Google, we recognize two distinct user cohorts:

1. **The Everyday Curator (Family Archivist, Photographer, Consumer):**
   - **Core Fear:** Accidentally deleting the better/original photo, losing memories, or keeping a compressed low-res copy instead of the high-res original.
   - **Need:** High visual reassurance, automated "Top Shot" keeper recommendations, side-by-side quality diffs, and reversible 30-day trash.
2. **The Power Storage Optimizer (Prosumer, Developer, Homelabber):**
   - **Core Fear:** Wasting hours manually clicking duplicates, high cognitive friction, sluggish UI, and unverified clobbering.
   - **Need:** 1-Click zero-risk batch cleanup for 100% exact clones, high-density data tables, keyboard shortcuts, hardlinking, and set-and-forget autonomous background surveillance.

### Core Product Tenet: "Automate the Obvious, Elevate the Nuanced"
- **The Obvious:** 100% exact byte-for-byte clones require **zero human cognitive effort**. One click cleans gigabytes with absolute mathematical safety.
- **The Nuanced:** Perceptual near-duplicates, burst shots, and re-encoded videos deserve **an elite, side-by-side inspection studio** that makes decision-making effortless.

---

## 2. The Four Pillar PM Decisions

```
+---------------------------------------------------------------------------------------------------------------+
|                                      THE 4 PILLARS OF CLAIRVOY STUDIO UX                                      |
+---------------------------------------------------------------------------------------------------------------+
|                                                                                                               |
|  PILLAR 1: Google One Smart Clean Triage      PILLAR 2: Google Photos Top Shot Studio                         |
|  * 2-Track Triage (Exact vs Similar)          * Side-by-side candidate vs keeper diff                         |
|  * 1-Click batch clean for exact clones       * Synchronized split-screen zoom loupe                          |
|  * Storage quota recovery impact projection   * Quality winner badges (Resolution, EXIF, Depth)               |
|                                                                                                               |
|  PILLAR 3: Google Drive Structured Workspace  PILLAR 4: Google Ambient Telemetry & Safety                     |
|  * Fluid Masonry Grid <--> Dense Table toggle * Floating bottom telemetry dock (Watcher & Sync)               |
|  * Sortable metadata columns & breadcrumbs    * Progressive friction ladder (Undo Trash -> Hardlink -> Purge) |
|  * Power keyboard shortcuts (J/K/Space/Del)   * Monospace SQLite WAL manifests & offline verification         |
+---------------------------------------------------------------------------------------------------------------+
```

---

## 3. Pillar 1: Google One Smart Clean Triage

### Architecture & Mechanics
Rather than dumping thousands of duplicate files into a flat list, Clairvoy presents a **Hero Storage Recovery Card** modeled directly on `one.google.com/storage/management`:

```
+---------------------------------------------------------------------------------------------------------------+
|                                      GOOGLE ONE STORAGE RECOVERY HERO                                         |
+---------------------------------------------------------------------------------------------------------------+
| Clean up 5.43 GB of unneeded storage across your scanned libraries                                            |
|                                                                                                               |
| Storage Projection Gauge:                                                                                     |
| [ Current Used: 124.5 GB ====================================================================> ]             |
| [ After Cleanup: 119.1 GB =========================================================> ] (🟢 5.43 GB Recoverable) |
+---------------------------------------------------------------------------------------------------------------+
| TRACK A: 100% Exact Clones (Zero Risk)        | TRACK B: Similar & Burst Photos (Assisted Review)             |
|                                               |                                                               |
|  ⚡ 142 duplicate files in 68 groups          |  🔍 48 visually similar photo sets in 18 groups               |
|  💾 4.28 GB recoverable space                |  💾 1.15 GB potential savings                                |
|  🛡️ Bit-for-bit verified identical           |  👁️ Best shot pre-selected; human inspection recommended    |
|                                               |                                                               |
|  [ 🗑️ Clean All Exact Duplicates (4.28 GB) ]  |  [ 🖼️ Review Similar Photos Set-by-Set (1.15 GB) ]            |
|  Action: Safely trashes duplicates in 1 click |  Action: Launches Side-by-Side Comparison Studio              |
+-----------------------------------------------+---------------------------------------------------------------+
```

### PM Requirements for Track A (Exact Clean):
- **1-Click Execution:** Trashes all duplicate files in exact hash clusters with a single confirmation modal.
- **Strict Invariant:** The designated `KEEPER` in every single cluster is permanently locked and protected against deletion.
- **Instant Undo:** Trashed files are moved into `.clairvoy_trash/` with a floating Google-style undo snackbar (`"142 duplicate files moved to trash (4.28 GB freed). [Undo]"`).

---

## 4. Pillar 2: Google Photos Top Shot Comparison Studio

### Architecture & Mechanics
When reviewing Track B (Similar & Burst Photos), clicking on any cluster opens a full-screen **Side-by-Side Comparison Studio** modeled on Google Photos Top Shot:

```
+---------------------------------------------------------------------------------------------------------------+
|                                    SIDE-BY-SIDE COMPARISON STUDIO (MODAL)                                     |
+---------------------------------------------------------------------------------------------------------------+
| [ Cluster 14: 3 Similar Photos • Match Score: 96.4% ]                                  [ ✕ Close / Esc ]      |
+---------------------------------------------------------------------------------------------------------------+
| CANDIDATE COPY (To be removed)                | DESIGNATED KEEPER (Best Shot / Protected)                     |
|                                               |                                                               |
| +-------------------------------------------+ | +-------------------------------------------+                 |
| |                                           | | |                                           |                 |
| |             [ Candidate Image ]           | | |              [ Keeper Image ]             |                 |
| |                                           | | |                                           |                 |
| +-------------------------------------------+ | +-------------------------------------------+                 |
|  Path: /backup/2024/IMG_0192_edited.jpg       |  Path: /photos/originals/IMG_0192.jpg                         |
|  Resolution: 2048 x 1536 (3.1 MP)             |  Resolution: 4032 x 3024 (12.2 MP)  [ 🟢 Higher Resolution ]  |
|  File Size:  1.42 MB                          |  File Size:  4.85 MB                [ 🟢 Higher Bitrate ]     |
|  Modified:   2024-05-12 14:20                 |  Modified:   2024-05-12 14:15       [ 🟢 Older Original ]     |
|                                               |                                                               |
|  Selection: [✓] Marked for Cleanup            |  Selection: [★ DESIGNATED KEEPER] (Click to make Keeper)      |
+---------------------------------------------------------------------------------------------------------------+
| Synchronized Inspection Toolbar:                                                                              |
| [ 🔍 Split Zoom: 1x | 2x | 4x ]  [ ⇄ Swap Keeper ]  |  [ < Prev Set (←) ]  Set 3 of 18  [ Next Set (→) > ]     |
+---------------------------------------------------------------------------------------------------------------+
```

### PM Requirements for Comparison Studio:
1. **Automated Advantage Badges:**
   - Automatically compares metadata and renders pill badges: `🟢 Higher Resolution`, `🟢 Higher Bitrate`, `🟢 Older Original Date`, `🟢 Uncompressed / RAW`.
2. **Synchronized Split Loupe Zoom:**
   - Moving the cursor or wheel zooming over Candidate image pans and zooms the Keeper image at the exact matching relative percentage coordinates, enabling instantaneous pixel-level comparison of sharpness and facial focus.
3. **1-Click Keeper Reassignment:**
   - Clicking `Make Keeper` on the candidate immediately promotes it, demotes the prior keeper, updates the SQLite manifest, and marks the other copy as duplicate.
4. **Rapid Keyboard Navigation:**
   - Left/Right arrows (`←` / `→`) transition to the previous/next cluster.
   - `Space` toggles candidate selection for deletion.
   - `K` swaps the keeper role.

---

## 5. Pillar 3: Google Drive Structured Workspace

### Architecture & Mechanics
Power users managing documents, video directories, archives, and system files require dense, sortable data organization. Clairvoy provides a seamless toolbar toggle between **Visual Masonry Grid** and **High-Density Table View**:

```
+---------------------------------------------------------------------------------------------------------------+
|                                         GOOGLE DRIVE STRUCTURED VIEW                                          |
+---------------------------------------------------------------------------------------------------------------+
| Breadcrumb: 🏠 Home > Pictures > Holidays 2024                                                                 |
| View Switcher: [ ▦ Grid ] [ ☰ Table ]   Sort: [ Recoverable Space v ]   Category: [ All Media v ]             |
+---------------------------------------------------------------------------------------------------------------+
| [ ] | Role   | File Name & Directory Path        | Size     | Resolution | Confidence | Quick Actions         |
|-----+--------+-----------------------------------+----------+------------+------------+-----------------------|
| [ ] | ★ KEEP | /photos/2024/DSC_001.JPG          | 6.2 MB   | 24.1 MP    | Original   | [ 👁️ Compare ] [ 📁 ]  |
| [✓] | ⚠️ DUP | /backup/copy_DSC_001.JPG          | 6.2 MB   | 24.1 MP    | Exact 100% | [ 👁️ Compare ] [ 🗑️ ]  |
| [✓] | ⚠️ DUP | /temp/export/DSC_001_small.JPG    | 1.1 MB   | 2.0 MP     | Similar 96%| [ 👁️ Compare ] [ 🗑️ ]  |
|-----+--------+-----------------------------------+----------+------------+------------+-----------------------|
| [ ] | ★ KEEP | /videos/Projects/Render_Final.mp4 | 1.84 GB  | 4K (60fps) | Original   | [ 🎬 Preview ] [ 📁 ]  |
| [✓] | ⚠️ DUP | /downloads/Render_Final_copy.mp4  | 1.84 GB  | 4K (60fps) | Exact 100% | [ 🎬 Preview ] [ 🗑️ ]  |
+---------------------------------------------------------------------------------------------------------------+
| Bulk Selection Bar (Google Photos style): 4 files selected (2.95 GB) [ 🗑️ Move to Trash ] [ 🔗 Hardlink ]      |
+---------------------------------------------------------------------------------------------------------------+
```

### PM Requirements for Structured View:
1. **Interactive Column Headers:**
   - Sortable by File Name, Recoverable Size, Similarity Score, and Date Modified.
2. **Contextual Row Actions:**
   - Quick action icons appear on hover: `Compare (👁️)`, `Reveal in Drive (📁)`, `Quick Trash (🗑️)`.
3. **Hardlink Optimization Option:**
   - Allows users to replace exact duplicates with filesystem hardlinks (NTFS / ext4 / APFS), preserving file paths in both folders while reclaiming 100% of the underlying disk space.

---

## 6. Pillar 4: Google Ambient Telemetry Dock & Friction Ladder

### Architecture & Mechanics
Background surveillance and scan progress should be omnipresent yet completely non-intrusive, inspired by the **Google Cloud Console status dock**:

```
+---------------------------------------------------------------------------------------------------------------+
| FLOATING BOTTOM ACTIVITY DOCK (Google Cloud Console style):                                                  |
| 🟢 Watcher: Monitoring 2 dirs | ⚡ Inotify: Listening | Last sync: 42s ago (SQLite WAL)     [ ^ Activity Log ] |
+---------------------------------------------------------------------------------------------------------------+
```

### The Progressive Friction Safety Ladder:
To guarantee zero accidental data loss, destructive operations adhere to a 3-step progressive friction ladder:

1. **Step 1: Soft Trash (Friction: Minimal / Reversible):**
   - Files are moved to `.clairvoy_trash/<timestamp>/` with an immediate undo snackbar.
   - Retained for 30 days before automatic purge.
2. **Step 2: Hardlink Conversion (Friction: Zero Data Risk):**
   - Replaces duplicate with a hardlink to the Keeper file.
   - Preserves all file trees, symlinks, and application paths; frees identical disk blocks.
3. **Step 3: Permanent Unlink (Friction: High / Safeguarded):**
   - High-contrast red warning dialog requiring explicit user confirmation.
   - Logs every unlinked inode to the SQLite audit database.

---

## 7. Delivery Roadmap & Implementation Phases

| Phase | Deliverable | Scope & Files |
|---|---|---|
| **Phase 1** | **Google One Smart Clean Two-Track Card** | Upgrade `#smartCleanHero` in `index.html` to support 1-Click Exact Batch Clean and Similar Review routing. |
| **Phase 2** | **Google Photos Side-by-Side Comparison Studio** | Upgrade lightbox modal in `index.html` with dual-image layout, metadata diff pills, synchronized zoom loupe, and star keeper swap. |
| **Phase 3** | **Google Drive Dense Table & Density Switcher** | Add full table rendering engine with sortable headers, breadcrumb trail, and row action triggers. |
| **Phase 4** | **Google Ambient Activity Dock & Safety Ladder** | Implement collapsible bottom dock for Watcher state and enhance Trash dialog with hardlinking option. |
