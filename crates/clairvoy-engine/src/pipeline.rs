use crate::keeper::CompositeKeeperStrategy;
use clairvoy_core::errors::EngineError;
use clairvoy_core::models::{ActionType, DuplicateRecord, FileEntry, MatchType, ScanSummary};
use clairvoy_core::traits::{KeeperStrategy, MatcherPlugin};
use clairvoy_scanner::scan_roots_with_progress;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

pub struct DeduplicationPipeline {
    target_paths: Vec<PathBuf>,
    matchers: Vec<Arc<dyn MatcherPlugin>>,
    keeper_strategy: Arc<dyn KeeperStrategy>,
}

impl DeduplicationPipeline {
    pub fn new(target_paths: Vec<PathBuf>) -> Self {
        Self {
            target_paths,
            matchers: Vec::new(),
            keeper_strategy: Arc::new(CompositeKeeperStrategy::new()),
        }
    }

    pub fn register_matcher(&mut self, matcher: Arc<dyn MatcherPlugin>) {
        self.matchers.push(matcher);
        self.matchers.sort_by_key(|m| m.priority_order());
    }

    pub fn set_keeper_strategy(&mut self, strategy: Arc<dyn KeeperStrategy>) {
        self.keeper_strategy = strategy;
    }

    pub fn run<F>(&self, mut progress_cb: F) -> Result<ScanSummary, EngineError>
    where
        F: FnMut(&str, usize, usize),
    {
        let t_start = Instant::now();
        progress_cb("Crawling filesystem", 0, self.target_paths.len());

        let (all_files, media_count) = scan_roots_with_progress(&self.target_paths, |cur, _| {
            progress_cb("Crawling filesystem", cur, 0);
        })?;
        progress_cb("Filesystem indexed", all_files.len(), all_files.len());

        let mut matched_paths: HashSet<PathBuf> = HashSet::new();
        let mut all_clusters = Vec::new();
        let total_matchers = self.matchers.len();

        for (idx, matcher) in self.matchers.iter().enumerate() {
            progress_cb(
                &format!("Running matcher: {}", matcher.display_name()),
                idx,
                total_matchers,
            );
            let candidates: Vec<FileEntry> = all_files
                .iter()
                .filter(|f| !matched_paths.contains(&f.path))
                .cloned()
                .collect();
            let supported = matcher.filter_supported(&candidates);
            if supported.len() >= 2 {
                let matcher_name = matcher.display_name();
                let clusters = matcher.find_duplicates_with_progress(&supported, &all_files, &mut |cur, tot| {
                    progress_cb(&format!("{}: hashing files", matcher_name), cur, tot);
                })?;
                for cluster in clusters {
                    for m in &cluster.members {
                        matched_paths.insert(m.path.clone());
                    }
                    all_clusters.push(cluster);
                }
            }
        }

        let total_clusters = all_clusters.len();
        progress_cb(
            "Scoring duplicate clusters",
            0,
            total_clusters,
        );
        let mut records = Vec::new();
        let mut total_wasted_bytes = 0u64;
        let mut category_breakdown = HashMap::new();

        for (cluster_idx, cluster) in all_clusters.iter().enumerate() {
            if (cluster_idx + 1) % 250 == 0 || cluster_idx + 1 == total_clusters {
                progress_cb(
                    "Scoring duplicate clusters",
                    cluster_idx + 1,
                    total_clusters,
                );
            }
            let group_id = cluster_idx + 1;
            let (keeper, dupes) = self.keeper_strategy.choose_keeper(&cluster.members);

            records.push(DuplicateRecord {
                group_id,
                match_type: cluster.match_type,
                action: ActionType::Keep,
                category: keeper.category,
                similarity: "100%".to_string(),
                similarity_score: 1.0,
                size_mb: (keeper.size_bytes as f64) / 1_048_576.0,
                path: keeper.path.to_string_lossy().to_string(),
                dimensions: None,
            });

            for d in dupes {
                total_wasted_bytes += d.size_bytes;
                *category_breakdown
                    .entry(format!("{:?}", d.category).to_uppercase())
                    .or_insert(0) += 1;
                records.push(DuplicateRecord {
                    group_id,
                    match_type: cluster.match_type,
                    action: ActionType::Duplicate,
                    category: d.category,
                    similarity: "100%".to_string(),
                    similarity_score: 1.0,
                    size_mb: (d.size_bytes as f64) / 1_048_576.0,
                    path: d.path.to_string_lossy().to_string(),
                    dimensions: None,
                });
            }
        }

        let elapsed = t_start.elapsed().as_secs_f64();
        let wasted_mb = (total_wasted_bytes as f64) / (1024.0 * 1024.0);
        let wasted_gb = wasted_mb / 1024.0;

        let exact_count = all_clusters
            .iter()
            .filter(|c| c.match_type == MatchType::ExactHash)
            .count();
        let visual_count = all_clusters
            .iter()
            .filter(|c| c.match_type == MatchType::VisualAiNearDuplicate)
            .count();
        let content_count = all_clusters
            .iter()
            .filter(|c| c.match_type == MatchType::ContentNearDuplicate)
            .count();

        Ok(ScanSummary {
            scanned_paths: self
                .target_paths
                .iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect(),
            scanned_dir: self
                .target_paths
                .first()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
            total_files_scanned: all_files.len(),
            media_files_scanned: media_count,
            exact_duplicate_groups: exact_count,
            visual_ai_groups: visual_count,
            content_duplicate_groups: content_count,
            total_duplicate_groups: all_clusters.len(),
            wasted_bytes: total_wasted_bytes,
            wasted_mb: (wasted_mb * 100.0).round() / 100.0,
            wasted_gb: (wasted_gb * 1000.0).round() / 1000.0,
            duration_seconds: (elapsed * 100.0).round() / 100.0,
            csv_report: None,
            summary_json: None,
            quarantine_script: None,
            groups: records,
            category_breakdown,
        })
    }
}
