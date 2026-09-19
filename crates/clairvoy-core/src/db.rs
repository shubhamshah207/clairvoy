use crate::errors::EngineError;
use crate::models::{ActionType, DuplicateRecord, ImageCategory, MatchType, ScanSummary};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, MutexGuard};

const SCHEMA_DDL: &str = r#"
CREATE TABLE IF NOT EXISTS watched_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    recursive BOOLEAN NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    last_scanned_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scan_runs (
    run_id TEXT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    scanned_paths TEXT NOT NULL,
    total_files INTEGER NOT NULL DEFAULT 0,
    duplicate_groups INTEGER NOT NULL DEFAULT 0,
    wasted_bytes INTEGER NOT NULL DEFAULT 0,
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'completed'
);

CREATE TABLE IF NOT EXISTS file_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    size_bytes INTEGER NOT NULL,
    modified_epoch INTEGER NOT NULL,
    quick_hash TEXT NOT NULL,
    full_hash TEXT,
    category TEXT NOT NULL,
    last_seen_run TEXT,
    FOREIGN KEY(last_seen_run) REFERENCES scan_runs(run_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_file_index_lookup ON file_index(path, size_bytes, modified_epoch);
CREATE INDEX IF NOT EXISTS idx_file_index_hashes ON file_index(quick_hash, full_hash);
CREATE INDEX IF NOT EXISTS idx_file_index_category ON file_index(category);

CREATE TABLE IF NOT EXISTS duplicate_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    cluster_id INTEGER NOT NULL,
    match_type TEXT NOT NULL,
    category TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    FOREIGN KEY(run_id) REFERENCES scan_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_clusters_run_cat ON duplicate_clusters(run_id, category);

CREATE TABLE IF NOT EXISTS duplicate_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    action TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    dimensions TEXT,
    FOREIGN KEY(cluster_id) REFERENCES duplicate_clusters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_duplicate_items_cluster ON duplicate_items(cluster_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_items_path ON duplicate_items(path);
"#;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WatchedPathRecord {
    pub id: i64,
    pub path: String,
    pub recursive: bool,
    pub enabled: bool,
    pub last_scanned_at: Option<String>,
    pub created_at: Option<String>,
}
pub type WatchedPath = WatchedPathRecord;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScanRunRecord {
    pub run_id: String,
    pub timestamp: String,
    pub scanned_paths: Vec<String>,
    pub total_files: usize,
    pub duplicate_groups: usize,
    pub wasted_bytes: u64,
    pub duration_seconds: f64,
    pub status: String,
}
pub type ScanRun = ScanRunRecord;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DuplicateItemRecord {
    pub id: i64,
    pub cluster_id: i64,
    pub path: String,
    pub action: String,
    pub size_bytes: u64,
    pub dimensions: Option<String>,
}
pub type DuplicateItem = DuplicateItemRecord;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DuplicateClusterRecord {
    pub id: i64,
    pub run_id: String,
    pub cluster_id: usize,
    pub match_type: String,
    pub category: String,
    pub similarity_score: f64,
    pub items: Vec<DuplicateItemRecord>,
}
pub type DuplicateClusterDb = DuplicateClusterRecord;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CachedFileRecord {
    pub id: i64,
    pub path: String,
    pub size_bytes: u64,
    pub modified_epoch: u64,
    pub quick_hash: String,
    pub full_hash: Option<String>,
    pub category: String,
    pub last_seen_run: Option<String>,
}
pub type CachedFile = CachedFileRecord;

#[derive(Debug, Clone)]
pub struct Database {
    conn: Arc<Mutex<Connection>>,
}

impl Database {
    pub fn default_path() -> PathBuf {
        let home = std::env::var("HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from("."));
        home.join(".clairvoy").join("clairvoy.db")
    }

    pub fn open(path: Option<&Path>) -> Result<Self, EngineError> {
        let conn = match path {
            Some(p) => {
                if let Some(parent) = p.parent() {
                    if !parent.as_os_str().is_empty() {
                        std::fs::create_dir_all(parent)?;
                    }
                }
                Connection::open(p)?
            }
            None => {
                let default = Self::default_path();
                if let Some(parent) = default.parent() {
                    if !parent.as_os_str().is_empty() {
                        std::fs::create_dir_all(parent)?;
                    }
                }
                Connection::open(&default)?
            }
        };

        let db = Self {
            conn: Arc::new(Mutex::new(conn)),
        };
        db.apply_pragmas()?;
        db.init_schema()?;
        Ok(db)
    }

    pub fn open_in_memory() -> Result<Self, EngineError> {
        let conn = Connection::open_in_memory()?;
        let db = Self {
            conn: Arc::new(Mutex::new(conn)),
        };
        db.apply_pragmas()?;
        db.init_schema()?;
        Ok(db)
    }

    fn get_conn(&self) -> Result<MutexGuard<'_, Connection>, EngineError> {
        self.conn
            .lock()
            .map_err(|e| EngineError::Config(format!("Database lock poisoned: {e}")))
    }

    fn apply_pragmas(&self) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             PRAGMA synchronous = NORMAL;
             PRAGMA temp_store = MEMORY;
             PRAGMA cache_size = -64000;
             PRAGMA foreign_keys = ON;",
        )?;
        Ok(())
    }

    pub fn init_schema(&self) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        conn.execute_batch(SCHEMA_DDL)?;
        Ok(())
    }

    // -------------------------------------------------------------------------
    // Watched Paths
    // -------------------------------------------------------------------------

    pub fn add_watched_path(&self, path: &str, recursive: bool) -> Result<i64, EngineError> {
        let conn = self.get_conn()?;
        let id: i64 = conn.query_row(
            "INSERT INTO watched_paths (path, recursive, enabled) VALUES (?1, ?2, 1)
             ON CONFLICT(path) DO UPDATE SET enabled = 1, recursive = excluded.recursive
             RETURNING id",
            params![path, recursive],
            |row| row.get(0),
        )?;
        Ok(id)
    }

    pub fn list_watched_paths(&self) -> Result<Vec<WatchedPathRecord>, EngineError> {
        let conn = self.get_conn()?;
        let mut stmt = conn.prepare(
            "SELECT id, path, recursive, enabled, last_scanned_at, created_at
             FROM watched_paths ORDER BY id ASC",
        )?;
        let rows = stmt.query_map([], |row| {
            Ok(WatchedPathRecord {
                id: row.get(0)?,
                path: row.get(1)?,
                recursive: row.get(2)?,
                enabled: row.get(3)?,
                last_scanned_at: row.get(4)?,
                created_at: row.get(5)?,
            })
        })?;
        let mut list = Vec::new();
        for r in rows {
            list.push(r?);
        }
        Ok(list)
    }

    pub fn toggle_watched_path(&self, id: i64, enabled: bool) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        conn.execute(
            "UPDATE watched_paths SET enabled = ?1 WHERE id = ?2",
            params![enabled, id],
        )?;
        Ok(())
    }

    pub fn remove_watched_path(&self, id: i64) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        conn.execute("DELETE FROM watched_paths WHERE id = ?1", params![id])?;
        Ok(())
    }

    pub fn update_watched_path_last_scanned(&self, id: i64) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        conn.execute(
            "UPDATE watched_paths SET last_scanned_at = CURRENT_TIMESTAMP WHERE id = ?1",
            params![id],
        )?;
        Ok(())
    }

    // -------------------------------------------------------------------------
    // Scan Runs
    // -------------------------------------------------------------------------

    pub fn insert_scan_run(&self, record: &ScanRunRecord) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        let paths_json = serde_json::to_string(&record.scanned_paths)?;
        conn.execute(
            "INSERT INTO scan_runs (run_id, timestamp, scanned_paths, total_files, duplicate_groups, wasted_bytes, duration_seconds, status)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
             ON CONFLICT(run_id) DO UPDATE SET
                timestamp = excluded.timestamp,
                scanned_paths = excluded.scanned_paths,
                total_files = excluded.total_files,
                duplicate_groups = excluded.duplicate_groups,
                wasted_bytes = excluded.wasted_bytes,
                duration_seconds = excluded.duration_seconds,
                status = excluded.status",
            params![
                record.run_id,
                record.timestamp,
                paths_json,
                record.total_files as i64,
                record.duplicate_groups as i64,
                record.wasted_bytes as i64,
                record.duration_seconds,
                record.status,
            ],
        )?;
        Ok(())
    }

    pub fn save_scan_run(&self, run_id: &str, summary: &ScanSummary) -> Result<(), EngineError> {
        let mut conn = self.get_conn()?;
        let tx = conn.transaction()?;

        let paths_json = serde_json::to_string(&summary.scanned_paths)?;
        tx.execute(
            "INSERT INTO scan_runs (run_id, timestamp, scanned_paths, total_files, duplicate_groups, wasted_bytes, duration_seconds, status)
             VALUES (?1, datetime('now'), ?2, ?3, ?4, ?5, ?6, 'completed')
             ON CONFLICT(run_id) DO UPDATE SET
                timestamp = datetime('now'),
                scanned_paths = excluded.scanned_paths,
                total_files = excluded.total_files,
                duplicate_groups = excluded.duplicate_groups,
                wasted_bytes = excluded.wasted_bytes,
                duration_seconds = excluded.duration_seconds,
                status = excluded.status",
            params![
                run_id,
                paths_json,
                summary.total_files_scanned as i64,
                summary.total_duplicate_groups as i64,
                summary.wasted_bytes as i64,
                summary.duration_seconds,
            ],
        )?;

        // Remove previous clusters/items for this run if any
        tx.execute(
            "DELETE FROM duplicate_clusters WHERE run_id = ?1",
            params![run_id],
        )?;

        // Group records by group_id preserving order
        let mut grouped: BTreeMap<usize, Vec<&DuplicateRecord>> = BTreeMap::new();
        for record in &summary.groups {
            grouped.entry(record.group_id).or_default().push(record);
        }

        for (group_id, items) in grouped {
            if items.is_empty() {
                continue;
            }
            let first = items[0];
            let match_type_str = match first.match_type {
                MatchType::ExactHash => "EXACT_HASH",
                MatchType::VisualAiNearDuplicate => "VISUAL_AI_NEAR_DUPLICATE",
                MatchType::ContentNearDuplicate => "CONTENT_NEAR_DUPLICATE",
            };
            let category_str = match first.category {
                ImageCategory::Photo => "PHOTO",
                ImageCategory::Video => "VIDEO",
                ImageCategory::Screenshot => "SCREENSHOT",
                ImageCategory::Document => "DOCUMENT",
                ImageCategory::Graphic => "GRAPHIC",
                ImageCategory::File => "FILE",
            };

            let cluster_pk: i64 = tx.query_row(
                "INSERT INTO duplicate_clusters (run_id, cluster_id, match_type, category, similarity_score)
                 VALUES (?1, ?2, ?3, ?4, ?5)
                 RETURNING id",
                params![
                    run_id,
                    group_id as i64,
                    match_type_str,
                    category_str,
                    first.similarity_score,
                ],
                |row| row.get(0),
            )?;

            for item in items {
                let action_str = match item.action {
                    ActionType::Keep => "KEEP",
                    ActionType::Duplicate => "DUPLICATE",
                };
                let size_bytes = (item.size_mb * 1048576.0).round() as i64;
                tx.execute(
                    "INSERT INTO duplicate_items (cluster_id, path, action, size_bytes, dimensions)
                     VALUES (?1, ?2, ?3, ?4, ?5)",
                    params![
                        cluster_pk,
                        item.path,
                        action_str,
                        size_bytes,
                        item.dimensions,
                    ],
                )?;
            }
        }

        tx.commit()?;
        Ok(())
    }

    pub fn list_scan_runs(&self, limit: usize) -> Result<Vec<ScanRunRecord>, EngineError> {
        let conn = self.get_conn()?;
        let mut stmt = conn.prepare(
            "SELECT run_id, timestamp, scanned_paths, total_files, duplicate_groups, wasted_bytes, duration_seconds, status
             FROM scan_runs
             ORDER BY timestamp DESC
             LIMIT ?1",
        )?;
        let rows = stmt.query_map(params![limit as i64], |row| {
            let paths_json: String = row.get(2)?;
            let scanned_paths: Vec<String> = serde_json::from_str(&paths_json).unwrap_or_default();
            let total_files: i64 = row.get(3)?;
            let duplicate_groups: i64 = row.get(4)?;
            let wasted_bytes: i64 = row.get(5)?;
            Ok(ScanRunRecord {
                run_id: row.get(0)?,
                timestamp: row.get(1)?,
                scanned_paths,
                total_files: total_files as usize,
                duplicate_groups: duplicate_groups as usize,
                wasted_bytes: wasted_bytes as u64,
                duration_seconds: row.get(6)?,
                status: row.get(7)?,
            })
        })?;
        let mut runs = Vec::new();
        for r in rows {
            runs.push(r?);
        }
        Ok(runs)
    }

    pub fn get_scan_run(&self, run_id: &str) -> Result<Option<ScanRunRecord>, EngineError> {
        let conn = self.get_conn()?;
        let mut stmt = conn.prepare(
            "SELECT run_id, timestamp, scanned_paths, total_files, duplicate_groups, wasted_bytes, duration_seconds, status
             FROM scan_runs
             WHERE run_id = ?1",
        )?;
        let mut rows = stmt.query(params![run_id])?;
        if let Some(row) = rows.next()? {
            let paths_json: String = row.get(2)?;
            let scanned_paths: Vec<String> = serde_json::from_str(&paths_json).unwrap_or_default();
            let total_files: i64 = row.get(3)?;
            let duplicate_groups: i64 = row.get(4)?;
            let wasted_bytes: i64 = row.get(5)?;
            Ok(Some(ScanRunRecord {
                run_id: row.get(0)?,
                timestamp: row.get(1)?,
                scanned_paths,
                total_files: total_files as usize,
                duplicate_groups: duplicate_groups as usize,
                wasted_bytes: wasted_bytes as u64,
                duration_seconds: row.get(6)?,
                status: row.get(7)?,
            }))
        } else {
            Ok(None)
        }
    }

    pub fn delete_scan_run(&self, run_id: &str) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        conn.execute("DELETE FROM scan_runs WHERE run_id = ?1", params![run_id])?;
        Ok(())
    }

    // -------------------------------------------------------------------------
    // Duplicate Clusters & Items
    // -------------------------------------------------------------------------

    pub fn insert_duplicate_record(
        &self,
        cluster_pk: i64,
        record: &DuplicateRecord,
    ) -> Result<i64, EngineError> {
        let conn = self.get_conn()?;
        let action_str = match record.action {
            ActionType::Keep => "KEEP",
            ActionType::Duplicate => "DUPLICATE",
        };
        let size_bytes = (record.size_mb * 1048576.0).round() as i64;
        let id: i64 = conn.query_row(
            "INSERT INTO duplicate_items (cluster_id, path, action, size_bytes, dimensions)
             VALUES (?1, ?2, ?3, ?4, ?5)
             RETURNING id",
            params![
                cluster_pk,
                record.path,
                action_str,
                size_bytes,
                record.dimensions,
            ],
            |row| row.get(0),
        )?;
        Ok(id)
    }

    pub fn get_clusters_for_run(
        &self,
        run_id: &str,
        category: Option<&str>,
        offset: usize,
        limit: usize,
    ) -> Result<Vec<DuplicateClusterRecord>, EngineError> {
        let conn = self.get_conn()?;
        let mut clusters = Vec::new();

        if let Some(cat) = category {
            let mut stmt = conn.prepare(
                "SELECT id, run_id, cluster_id, match_type, category, similarity_score
                 FROM duplicate_clusters
                 WHERE run_id = ?1 AND category = ?2
                 ORDER BY id ASC
                 LIMIT ?3 OFFSET ?4",
            )?;
            let rows =
                stmt.query_map(params![run_id, cat, limit as i64, offset as i64], |row| {
                    let id: i64 = row.get(0)?;
                    let run_id: String = row.get(1)?;
                    let cluster_id: i64 = row.get(2)?;
                    let match_type: String = row.get(3)?;
                    let category: String = row.get(4)?;
                    let similarity_score: f64 = row.get(5)?;
                    Ok((
                        id,
                        run_id,
                        cluster_id as usize,
                        match_type,
                        category,
                        similarity_score,
                    ))
                })?;
            for r in rows {
                let (id, r_id, c_id, mt, cat, score) = r?;
                clusters.push(DuplicateClusterRecord {
                    id,
                    run_id: r_id,
                    cluster_id: c_id,
                    match_type: mt,
                    category: cat,
                    similarity_score: score,
                    items: Vec::new(),
                });
            }
        } else {
            let mut stmt = conn.prepare(
                "SELECT id, run_id, cluster_id, match_type, category, similarity_score
                 FROM duplicate_clusters
                 WHERE run_id = ?1
                 ORDER BY id ASC
                 LIMIT ?2 OFFSET ?3",
            )?;
            let rows = stmt.query_map(params![run_id, limit as i64, offset as i64], |row| {
                let id: i64 = row.get(0)?;
                let run_id: String = row.get(1)?;
                let cluster_id: i64 = row.get(2)?;
                let match_type: String = row.get(3)?;
                let category: String = row.get(4)?;
                let similarity_score: f64 = row.get(5)?;
                Ok((
                    id,
                    run_id,
                    cluster_id as usize,
                    match_type,
                    category,
                    similarity_score,
                ))
            })?;
            for r in rows {
                let (id, r_id, c_id, mt, cat, score) = r?;
                clusters.push(DuplicateClusterRecord {
                    id,
                    run_id: r_id,
                    cluster_id: c_id,
                    match_type: mt,
                    category: cat,
                    similarity_score: score,
                    items: Vec::new(),
                });
            }
        }

        let mut items_stmt = conn.prepare(
            "SELECT id, cluster_id, path, action, size_bytes, dimensions
             FROM duplicate_items
             WHERE cluster_id = ?1
             ORDER BY id ASC",
        )?;

        for cluster in &mut clusters {
            let rows = items_stmt.query_map(params![cluster.id], |row| {
                let size_bytes: i64 = row.get(4)?;
                Ok(DuplicateItemRecord {
                    id: row.get(0)?,
                    cluster_id: row.get(1)?,
                    path: row.get(2)?,
                    action: row.get(3)?,
                    size_bytes: size_bytes as u64,
                    dimensions: row.get(5)?,
                })
            })?;
            for item in rows {
                cluster.items.push(item?);
            }
        }

        Ok(clusters)
    }

    pub fn get_duplicate_clusters(
        &self,
        run_id: &str,
        category: Option<&str>,
        offset: usize,
        limit: usize,
    ) -> Result<Vec<DuplicateClusterRecord>, EngineError> {
        self.get_clusters_for_run(run_id, category, offset, limit)
    }

    pub fn get_cluster_count_for_run(
        &self,
        run_id: &str,
        category: Option<&str>,
    ) -> Result<usize, EngineError> {
        let conn = self.get_conn()?;
        let count: i64 = if let Some(cat) = category {
            conn.query_row(
                "SELECT COUNT(*) FROM duplicate_clusters WHERE run_id = ?1 AND category = ?2",
                params![run_id, cat],
                |row| row.get(0),
            )?
        } else {
            conn.query_row(
                "SELECT COUNT(*) FROM duplicate_clusters WHERE run_id = ?1",
                params![run_id],
                |row| row.get(0),
            )?
        };
        Ok(count as usize)
    }

    pub fn get_scan_summary(&self, run_id: &str) -> Result<Option<ScanSummary>, EngineError> {
        let run = match self.get_scan_run(run_id)? {
            Some(r) => r,
            None => return Ok(None),
        };
        let clusters = self.get_clusters_for_run(run_id, None, 0, 100_000)?;
        let mut groups = Vec::new();
        let mut category_breakdown = std::collections::HashMap::new();
        let mut exact_count = 0;
        let mut visual_count = 0;
        let mut content_count = 0;

        for c in clusters {
            let match_type = match c.match_type.as_str() {
                "EXACT_HASH" => {
                    exact_count += 1;
                    MatchType::ExactHash
                }
                "VISUAL_AI_NEAR_DUPLICATE" => {
                    visual_count += 1;
                    MatchType::VisualAiNearDuplicate
                }
                _ => {
                    content_count += 1;
                    MatchType::ContentNearDuplicate
                }
            };
            let category = match c.category.as_str() {
                "PHOTO" => ImageCategory::Photo,
                "VIDEO" => ImageCategory::Video,
                "SCREENSHOT" => ImageCategory::Screenshot,
                "DOCUMENT" => ImageCategory::Document,
                "GRAPHIC" => ImageCategory::Graphic,
                _ => ImageCategory::File,
            };

            for item in c.items {
                let action = if item.action == "KEEP" {
                    ActionType::Keep
                } else {
                    *category_breakdown.entry(c.category.clone()).or_insert(0) += 1;
                    ActionType::Duplicate
                };
                let sim_str = if (c.similarity_score - 1.0).abs() < 1e-4 {
                    "100%".to_string()
                } else {
                    format!("{:.0}%", c.similarity_score * 100.0)
                };
                groups.push(DuplicateRecord {
                    group_id: c.cluster_id,
                    match_type,
                    action,
                    category,
                    similarity: sim_str,
                    similarity_score: c.similarity_score,
                    size_mb: item.size_bytes as f64 / 1_048_576.0,
                    path: item.path,
                    dimensions: item.dimensions,
                });
            }
        }

        let wasted_mb = run.wasted_bytes as f64 / 1_048_576.0;
        let wasted_gb = run.wasted_bytes as f64 / 1_073_741_824.0;
        let first_path = run.scanned_paths.first().cloned().unwrap_or_default();

        Ok(Some(ScanSummary {
            scanned_paths: run.scanned_paths,
            scanned_dir: first_path,
            total_files_scanned: run.total_files,
            media_files_scanned: run.total_files,
            exact_duplicate_groups: exact_count,
            visual_ai_groups: visual_count,
            content_duplicate_groups: content_count,
            total_duplicate_groups: run.duplicate_groups,
            wasted_bytes: run.wasted_bytes,
            wasted_mb,
            wasted_gb,
            duration_seconds: run.duration_seconds,
            csv_report: None,
            summary_json: None,
            quarantine_script: None,
            groups,
            category_breakdown,
        }))
    }

    pub fn override_keeper(
        &self,
        cluster_id: i64,
        new_keeper_path: &str,
    ) -> Result<(), EngineError> {
        let mut conn = self.get_conn()?;
        let tx = conn.transaction()?;

        let exists: bool = tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM duplicate_items WHERE cluster_id = ?1 AND path = ?2)",
            params![cluster_id, new_keeper_path],
            |row| row.get(0),
        )?;

        if !exists {
            return Err(EngineError::Database(rusqlite::Error::QueryReturnedNoRows));
        }

        tx.execute(
            "UPDATE duplicate_items SET action = 'DUPLICATE' WHERE cluster_id = ?1",
            params![cluster_id],
        )?;

        tx.execute(
            "UPDATE duplicate_items SET action = 'KEEP' WHERE cluster_id = ?1 AND path = ?2",
            params![cluster_id, new_keeper_path],
        )?;

        tx.commit()?;
        Ok(())
    }

    pub fn remove_duplicate_items(&self, paths: &[String]) -> Result<(usize, u64), EngineError> {
        if paths.is_empty() {
            return Ok((0, 0));
        }
        let mut conn = self.get_conn()?;
        let tx = conn.transaction()?;

        let mut removed_count = 0;
        let mut freed_bytes = 0u64;

        for path in paths {
            let mut stmt = tx.prepare(
                "SELECT cluster_id, size_bytes, action FROM duplicate_items WHERE path = ?1",
            )?;
            let rows: Vec<(i64, i64, String)> = stmt
                .query_map(params![path], |row| {
                    Ok((row.get(0)?, row.get(1)?, row.get(2)?))
                })?
                .filter_map(|r| r.ok())
                .collect();

            for (_cluster_id, size, action) in rows {
                if action == "DUPLICATE" {
                    freed_bytes += size as u64;
                    removed_count += 1;
                }
            }

            tx.execute("DELETE FROM duplicate_items WHERE path = ?1", params![path])?;
            tx.execute("DELETE FROM file_index WHERE path = ?1", params![path])?;
        }

        // Delete any clusters that now have NO duplicates remaining (only keeper or empty)
        tx.execute(
            "DELETE FROM duplicate_clusters WHERE id IN (
                SELECT c.id FROM duplicate_clusters c
                LEFT JOIN duplicate_items i ON c.id = i.cluster_id AND i.action = 'DUPLICATE'
                GROUP BY c.id
                HAVING COUNT(i.id) = 0
            )",
            [],
        )?;

        // Update all scan_runs: recalculate duplicate_groups and wasted_bytes from remaining items!
        tx.execute(
            "UPDATE scan_runs SET
                duplicate_groups = (
                    SELECT COUNT(DISTINCT c.id)
                    FROM duplicate_clusters c
                    JOIN duplicate_items i ON c.id = i.cluster_id
                    WHERE c.run_id = scan_runs.run_id AND i.action = 'DUPLICATE'
                ),
                wasted_bytes = COALESCE((
                    SELECT SUM(i.size_bytes)
                    FROM duplicate_clusters c
                    JOIN duplicate_items i ON c.id = i.cluster_id
                    WHERE c.run_id = scan_runs.run_id AND i.action = 'DUPLICATE'
                ), 0)
            ",
            [],
        )?;

        tx.commit()?;
        Ok((removed_count, freed_bytes))
    }

    pub fn prune_missing_files(&self) -> Result<(usize, u64), EngineError> {
        let paths: Vec<String> = {
            let conn = self.get_conn()?;
            let mut stmt = conn
                .prepare("SELECT DISTINCT path FROM duplicate_items WHERE action = 'DUPLICATE'")?;
            let rows = stmt.query_map([], |row| row.get(0))?;
            rows.filter_map(|r| r.ok()).collect()
        };

        let missing: Vec<String> = paths
            .into_iter()
            .filter(|p| !Path::new(p).exists())
            .collect();
        if missing.is_empty() {
            return Ok((0, 0));
        }
        self.remove_duplicate_items(&missing)
    }

    // -------------------------------------------------------------------------
    // File Index (Delta Deduplication Cache)
    // -------------------------------------------------------------------------

    pub fn get_cached_file(&self, path: &str) -> Result<Option<CachedFileRecord>, EngineError> {
        let conn = self.get_conn()?;
        let mut stmt = conn.prepare(
            "SELECT id, path, size_bytes, modified_epoch, quick_hash, full_hash, category, last_seen_run
             FROM file_index
             WHERE path = ?1",
        )?;
        let mut rows = stmt.query(params![path])?;
        if let Some(row) = rows.next()? {
            let size_bytes: i64 = row.get(2)?;
            let modified_epoch: i64 = row.get(3)?;
            Ok(Some(CachedFileRecord {
                id: row.get(0)?,
                path: row.get(1)?,
                size_bytes: size_bytes as u64,
                modified_epoch: modified_epoch as u64,
                quick_hash: row.get(4)?,
                full_hash: row.get(5)?,
                category: row.get(6)?,
                last_seen_run: row.get(7)?,
            }))
        } else {
            Ok(None)
        }
    }

    pub fn upsert_file_index(&self, entry: &CachedFileRecord) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        conn.execute(
            "INSERT INTO file_index (path, size_bytes, modified_epoch, quick_hash, full_hash, category, last_seen_run)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
             ON CONFLICT(path) DO UPDATE SET
                size_bytes = excluded.size_bytes,
                modified_epoch = excluded.modified_epoch,
                quick_hash = excluded.quick_hash,
                full_hash = excluded.full_hash,
                category = excluded.category,
                last_seen_run = excluded.last_seen_run",
            params![
                entry.path,
                entry.size_bytes as i64,
                entry.modified_epoch as i64,
                entry.quick_hash,
                entry.full_hash,
                entry.category,
                entry.last_seen_run,
            ],
        )?;
        Ok(())
    }

    pub fn delete_cached_file(&self, path: &str) -> Result<(), EngineError> {
        let conn = self.get_conn()?;
        conn.execute("DELETE FROM file_index WHERE path = ?1", params![path])?;
        Ok(())
    }
}
