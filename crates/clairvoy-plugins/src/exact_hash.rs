use clairvoy_core::errors::EngineError;
use clairvoy_core::models::{DuplicateCluster, FileEntry, MatchType};
use clairvoy_core::traits::MatcherPlugin;
use rayon::prelude::*;
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read};
use std::path::Path;

pub struct ExactHashMatcherPlugin {
    priority: u32,
}

impl ExactHashMatcherPlugin {
    pub fn new() -> Self {
        Self { priority: 10 }
    }

    fn compute_blake3_hash(path: &Path) -> io::Result<[u8; 32]> {
        let mut file = File::open(path)?;
        let mut hasher = blake3::Hasher::new();
        let mut buf = [0u8; 65536];
        loop {
            let n = file.read(&mut buf)?;
            if n == 0 {
                break;
            }
            hasher.update(&buf[..n]);
        }
        Ok(*hasher.finalize().as_bytes())
    }
}

impl Default for ExactHashMatcherPlugin {
    fn default() -> Self {
        Self::new()
    }
}

impl MatcherPlugin for ExactHashMatcherPlugin {
    fn plugin_id(&self) -> &str {
        "exact_hash"
    }

    fn display_name(&self) -> &str {
        "Byte-Exact Hash Matcher (BLAKE3 SIMD)"
    }

    fn priority_order(&self) -> u32 {
        self.priority
    }

    fn match_type(&self) -> MatchType {
        MatchType::ExactHash
    }

    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry> {
        files.iter().filter(|f| f.size_bytes > 0).cloned().collect()
    }

    fn find_duplicates(
        &self,
        candidates: &[FileEntry],
        _all_files: &[FileEntry],
    ) -> Result<Vec<DuplicateCluster>, EngineError> {
        // Step 1: Group by file size in bytes (O(1) pre-filter)
        // Defense-in-depth: ignore 0-byte files so they never form duplicate clusters
        let mut size_map: HashMap<u64, Vec<&FileEntry>> = HashMap::new();
        for entry in candidates {
            if entry.size_bytes > 0 {
                size_map.entry(entry.size_bytes).or_default().push(entry);
            }
        }

        // Keep only size groups with >= 2 files
        let candidate_groups: Vec<Vec<&FileEntry>> =
            size_map.into_values().filter(|g| g.len() >= 2).collect();

        let mut clusters = Vec::new();
        let mut next_id = 1;

        // Step 2: Compute full BLAKE3 digests in parallel
        for group in candidate_groups {
            let hashed: Vec<([u8; 32], &FileEntry)> = group
                .par_iter()
                .filter_map(|e| Self::compute_blake3_hash(&e.path).ok().map(|h| (h, *e)))
                .collect();

            let mut hash_map: HashMap<[u8; 32], Vec<FileEntry>> = HashMap::new();
            for (hash, entry) in hashed {
                hash_map.entry(hash).or_default().push(entry.clone());
            }

            for (_, members) in hash_map {
                if members.len() >= 2 {
                    let len = members.len();
                    clusters.push(DuplicateCluster {
                        cluster_id: next_id,
                        match_type: MatchType::ExactHash,
                        members,
                        similarity_scores: vec![1.0; len],
                        metadata: HashMap::new(),
                    });
                    next_id += 1;
                }
            }
        }

        Ok(clusters)
    }
}
