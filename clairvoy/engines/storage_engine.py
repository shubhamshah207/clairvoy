"""
Clairvoy Storage Core Engine
Combines exact content hash verification (SHA-256) with local Vision AI (DINOv2).
"""

import os
import hashlib
import re
import csv
import json
import time
from collections import defaultdict
from clairvoy.engines.vision_engine import VisionEngine, HAS_ML

EXCLUDED_DIRS = {"_logs", "_zips", "_dedupe_reports", "_duplicate_quarantine", ".git", "__pycache__"}
MEDIA_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp"
}

class StorageEngine:
    def __init__(self, base_dir, output_dir=None, enable_ml=True, ml_threshold=0.95):
        self.base_dir = os.path.abspath(base_dir)
        self.output_dir = os.path.abspath(output_dir or os.path.join(self.base_dir, "_dedupe_reports"))
        self.enable_ml = enable_ml and HAS_ML
        self.ml_threshold = ml_threshold
        os.makedirs(self.output_dir, exist_ok=True)

    def get_quick_hash(self, path):
        h = hashlib.md5()
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size <= 128 * 1024:
                h.update(f.read())
            else:
                h.update(f.read(64 * 1024))
                f.seek(size - 64 * 1024)
                h.update(f.read(64 * 1024))
        return h.hexdigest()

    def get_full_sha256(self, path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest()

    def score_file_keeper(self, path):
        score = 100
        norm_path = path.replace("\\", "/").lower()
        if "/trash/" in norm_path:
            score -= 500
        if "photos from " in norm_path:
            score += 30
        filename = os.path.basename(path)
        if re.search(r"\(\d+\)", filename):
            score -= 15
        if "-edited" in filename.lower():
            score -= 10
        return score

    def run(self):
        print(f"[*] Scanning: {self.base_dir}")
        start_time = time.time()

        all_files = []
        media_files = []
        for root, dirs, files in os.walk(self.base_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for f in files:
                if f.endswith(".json") or f.endswith(".ini"):
                    continue
                p = os.path.join(root, f)
                try:
                    sz = os.path.getsize(p)
                    if sz > 0:
                        all_files.append((p, sz))
                        ext = os.path.splitext(f)[1].lower()
                        if ext in MEDIA_EXTS:
                            media_files.append(p)
                except Exception:
                    pass

        print(f"[*] Indexed {len(all_files)} files ({len(media_files)} media files).")
        print("[*] Stage 1: Detecting exact content duplicates (SHA-256)...")

        size_map = defaultdict(list)
        for path, sz in all_files:
            size_map[sz].append(path)

        quick_map = defaultdict(list)
        for sz, paths in size_map.items():
            if len(paths) > 1:
                for p in paths:
                    try:
                        qh = self.get_quick_hash(p)
                        quick_map[(sz, qh)].append(p)
                    except Exception:
                        pass

        hash_groups = defaultdict(list)
        for (sz, qh), paths in quick_map.items():
            if len(paths) > 1:
                for p in paths:
                    try:
                        fhash = self.get_full_sha256(p)
                        hash_groups[(sz, fhash)].append(p)
                    except Exception:
                        pass

        exact_dupe_sets = [paths for paths in hash_groups.values() if len(paths) > 1]
        print(f"[✓] Stage 1 complete: {len(exact_dupe_sets)} exact duplicate sets found.")

        # Stage 2: Vision AI on remaining media files
        ml_clusters = []
        if self.enable_ml and media_files:
            exact_matched_files = {p for group in exact_dupe_sets for p in group}
            unmatched_media = [p for p in media_files if p not in exact_matched_files]
            if unmatched_media:
                print(f"[*] Stage 2: Running local Vision AI (DINOv2) on {len(unmatched_media)} photos...")
                try:
                    v_engine = VisionEngine(threshold=self.ml_threshold)
                    ml_clusters = v_engine.find_near_duplicates(unmatched_media)
                except Exception as e:
                    print(f"[!] Vision AI error: {e}")

        # Consolidate duplicate records
        duplicate_records = []
        group_id = 1
        total_wasted_bytes = 0
        quarantine_cmds = []

        # 1. Exact duplicates
        for paths in exact_dupe_sets:
            file_scores = sorted([(self.score_file_keeper(p), p) for p in paths], key=lambda x: x[0], reverse=True)
            keeper_path = file_scores[0][1]
            dupes = [x[1] for x in file_scores[1:]]

            duplicate_records.append({
                "group_id": group_id,
                "match_type": "EXACT_HASH",
                "action": "KEEP",
                "similarity": "100%",
                "path": keeper_path,
                "size_mb": round(os.path.getsize(keeper_path) / (1024*1024), 3)
            })

            for dp in dupes:
                dsize = os.path.getsize(dp)
                total_wasted_bytes += dsize
                duplicate_records.append({
                    "group_id": group_id,
                    "match_type": "EXACT_HASH",
                    "action": "DUPLICATE",
                    "similarity": "100%",
                    "path": dp,
                    "size_mb": round(dsize / (1024*1024), 3)
                })
                rel_dir = os.path.relpath(os.path.dirname(dp), self.base_dir)
                target_qdir = os.path.join(self.base_dir, "_duplicate_quarantine", rel_dir)
                quarantine_cmds.append(f'mkdir -p "{target_qdir}" && mv "{dp}" "{target_qdir}/"')

            group_id += 1

        # 2. Vision AI near-duplicates
        for group, scores, dims in ml_clusters:
            file_scores = sorted([(self.score_file_keeper(p), p, sc) for p, sc in zip(group, scores)], key=lambda x: x[0], reverse=True)
            keeper_path = file_scores[0][1]
            dupes = file_scores[1:]

            duplicate_records.append({
                "group_id": group_id,
                "match_type": "VISUAL_AI_NEAR_DUPLICATE",
                "action": "KEEP",
                "similarity": "100%",
                "path": keeper_path,
                "size_mb": round(os.path.getsize(keeper_path) / (1024*1024), 3)
            })

            for _, dp, sc in dupes:
                dsize = os.path.getsize(dp)
                total_wasted_bytes += dsize
                duplicate_records.append({
                    "group_id": group_id,
                    "match_type": "VISUAL_AI_NEAR_DUPLICATE",
                    "action": "DUPLICATE",
                    "similarity": f"{sc*100:.1f}%",
                    "path": dp,
                    "size_mb": round(dsize / (1024*1024), 3)
                })
                rel_dir = os.path.relpath(os.path.dirname(dp), self.base_dir)
                target_qdir = os.path.join(self.base_dir, "_duplicate_quarantine", rel_dir)
                quarantine_cmds.append(f'mkdir -p "{target_qdir}" && mv "{dp}" "{target_qdir}/"')

            group_id += 1

        # Save Reports
        csv_file = os.path.join(self.output_dir, "duplicates_report.csv")
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["group_id", "match_type", "action", "similarity", "size_mb", "path"])
            writer.writeheader()
            writer.writerows(duplicate_records)

        json_file = os.path.join(self.output_dir, "duplicates_summary.json")
        summary = {
            "total_files_scanned": len(all_files),
            "media_files_scanned": len(media_files),
            "exact_duplicate_groups": len(exact_dupe_sets),
            "visual_ai_groups": len(ml_clusters),
            "total_duplicate_groups": len(exact_dupe_sets) + len(ml_clusters),
            "wasted_mb": round(total_wasted_bytes / (1024*1024), 2),
            "wasted_gb": round(total_wasted_bytes / (1024*1024*1024), 3),
            "csv_report": csv_file,
            "groups": duplicate_records
        }
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        sh_file = os.path.join(self.output_dir, "quarantine_duplicates.sh")
        with open(sh_file, "w") as f:
            f.write("#!/usr/bin/env bash\nset -e\n")
            for cmd in quarantine_cmds:
                f.write(cmd + "\n")
        os.chmod(sh_file, 0o755)

        elapsed = time.time() - start_time
        print(f"\n[✓] Full scan completed in {elapsed:.1f}s")
        print(f" • Exact Duplicate Sets: {len(exact_dupe_sets)}")
        print(f" • Visual AI Clusters: {len(ml_clusters)}")
        print(f" • Total Recoverable Space: {summary['wasted_mb']} MB ({summary['wasted_gb']} GB)")
        print(f" • CSV Report: {csv_file}")
        print(f" • Summary JSON: {json_file}")
        print(f" • Safe Quarantine Script: {sh_file}")
        return summary
