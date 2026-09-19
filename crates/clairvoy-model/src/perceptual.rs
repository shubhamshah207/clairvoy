use crate::traits::ModelBackend;
use clairvoy_core::errors::EngineError;
use image_hasher::{HasherConfig, ImageHash};
use std::path::Path;

pub struct PerceptualHashBackend {
    hasher: image_hasher::Hasher,
}

impl PerceptualHashBackend {
    pub fn new() -> Self {
        Self {
            hasher: HasherConfig::new().hash_size(8, 8).to_hasher(),
        }
    }
}

impl Default for PerceptualHashBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl ModelBackend for PerceptualHashBackend {
    fn model_id(&self) -> &str {
        "perceptual_blockhash_64"
    }

    fn embedding_dim(&self) -> usize {
        64
    }

    fn embed_image(&self, path: &Path) -> Result<Vec<f32>, EngineError> {
        let img = image::open(path).map_err(|e| {
            EngineError::Model(format!("Image decode error {}: {}", path.display(), e))
        })?;
        let hash: ImageHash = self.hasher.hash_image(&img);
        let bytes = hash.as_bytes();
        let mut embedding = Vec::with_capacity(64);
        for byte in bytes {
            for bit in 0..8 {
                embedding.push(if (byte >> bit) & 1 == 1 { 1.0 } else { 0.0 });
            }
        }
        Ok(embedding)
    }
}
