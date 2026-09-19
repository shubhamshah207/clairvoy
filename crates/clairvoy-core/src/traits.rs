use crate::errors::EngineError;
use crate::models::{DuplicateCluster, FileEntry, MatchType, ScanSummary};
use std::path::Path;

pub trait MatcherPlugin: Send + Sync {
    fn plugin_id(&self) -> &str;
    fn display_name(&self) -> &str;
    fn priority_order(&self) -> u32;
    fn match_type(&self) -> MatchType;
    fn is_available(&self) -> (bool, String) {
        (true, "Ready".to_string())
    }
    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry>;
    fn find_duplicates(
        &self,
        candidates: &[FileEntry],
        all_files: &[FileEntry],
    ) -> Result<Vec<DuplicateCluster>, EngineError>;
    fn find_duplicates_with_progress(
        &self,
        candidates: &[FileEntry],
        all_files: &[FileEntry],
        _progress: &mut dyn FnMut(usize, usize),
    ) -> Result<Vec<DuplicateCluster>, EngineError> {
        self.find_duplicates(candidates, all_files)
    }
}

pub trait KeeperStrategy: Send + Sync {
    fn score_entry(&self, entry: &FileEntry, cluster: &[FileEntry]) -> i64;
    fn choose_keeper<'a>(&self, cluster: &'a [FileEntry]) -> (&'a FileEntry, Vec<&'a FileEntry>);
}

pub trait ActionHandler: Send + Sync {
    fn action_id(&self) -> &str;
    fn execute(
        &self,
        summary: &ScanSummary,
        base_dirs: &[&Path],
        dry_run: bool,
    ) -> Result<usize, EngineError>;
}
