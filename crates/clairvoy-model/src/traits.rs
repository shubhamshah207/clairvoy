use clairvoy_core::errors::EngineError;
use std::path::Path;

pub trait ModelBackend: Send + Sync {
    fn model_id(&self) -> &str;
    fn embedding_dim(&self) -> usize;
    fn embed_image(&self, path: &Path) -> Result<Vec<f32>, EngineError>;
}
