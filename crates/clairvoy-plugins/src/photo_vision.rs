use clairvoy_core::errors::EngineError;
use clairvoy_core::models::{DuplicateCluster, FileEntry, MatchType};
use clairvoy_core::traits::MatcherPlugin;
use clairvoy_model::ModelBackend;
use std::sync::Arc;

pub struct PhotoVisionMatcherPlugin {
    backend: Arc<dyn ModelBackend>,
    threshold: f32,
}

impl PhotoVisionMatcherPlugin {
    pub fn new(backend: Arc<dyn ModelBackend>, threshold: f32) -> Self {
        Self { backend, threshold }
    }

    pub fn backend(&self) -> &Arc<dyn ModelBackend> {
        &self.backend
    }

    pub fn threshold(&self) -> f32 {
        self.threshold
    }
}

impl MatcherPlugin for PhotoVisionMatcherPlugin {
    fn plugin_id(&self) -> &str {
        "photo_vision"
    }

    fn display_name(&self) -> &str {
        "Photo Vision Matcher (Pluggable Model)"
    }

    fn priority_order(&self) -> u32 {
        20
    }

    fn match_type(&self) -> MatchType {
        MatchType::VisualAiNearDuplicate
    }

    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry> {
        files.iter().filter(|f| f.is_media).cloned().collect()
    }

    fn find_duplicates(
        &self,
        _candidates: &[FileEntry],
        _all_files: &[FileEntry],
    ) -> Result<Vec<DuplicateCluster>, EngineError> {
        // Future batch cosine distance implementation
        Ok(Vec::new())
    }
}
