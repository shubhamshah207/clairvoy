use crate::perceptual::PerceptualHashBackend;
use crate::traits::ModelBackend;
use clairvoy_core::errors::EngineError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ModelConfig {
    pub backend: String,
    pub model_path: Option<String>,
    pub embedding_dim: usize,
    pub input_size: Option<[u32; 2]>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ModelsRegistryConfig {
    pub default_model: String,
    #[serde(default)]
    pub models: HashMap<String, ModelConfig>,
}

impl ModelsRegistryConfig {
    pub fn from_toml_str(content: &str) -> Result<Self, EngineError> {
        toml::from_str(content)
            .map_err(|e| EngineError::Config(format!("Failed to parse models TOML: {e}")))
    }

    pub fn load_from_file(path: &Path) -> Result<Self, EngineError> {
        let content = std::fs::read_to_string(path).map_err(EngineError::Io)?;
        Self::from_toml_str(&content)
    }
}

pub struct ModelRegistry {
    pub config: ModelsRegistryConfig,
}

impl ModelRegistry {
    pub fn new(config: ModelsRegistryConfig) -> Self {
        Self { config }
    }

    pub fn from_toml_str(content: &str) -> Result<Self, EngineError> {
        let config = ModelsRegistryConfig::from_toml_str(content)?;
        Ok(Self { config })
    }

    pub fn load_from_file(path: &Path) -> Result<Self, EngineError> {
        let config = ModelsRegistryConfig::load_from_file(path)?;
        Ok(Self { config })
    }

    pub fn create_backend(
        &self,
        model_name: Option<&str>,
    ) -> Result<Box<dyn ModelBackend>, EngineError> {
        let name = model_name.unwrap_or(&self.config.default_model);
        if let Some(model_cfg) = self.config.models.get(name) {
            match model_cfg.backend.as_str() {
                "perceptual" | "perceptual_hash" | "blockhash" => {
                    Ok(Box::new(PerceptualHashBackend::new()))
                }
                other => Err(EngineError::Config(format!(
                    "Unsupported model backend '{other}' for model '{name}'"
                ))),
            }
        } else if name == "perceptual" || name == "perceptual_blockhash_64" {
            Ok(Box::new(PerceptualHashBackend::new()))
        } else {
            Err(EngineError::Config(format!(
                "Model '{name}' not found in registry (default: '{}')",
                self.config.default_model
            )))
        }
    }
}
