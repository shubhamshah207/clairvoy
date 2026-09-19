use thiserror::Error;

#[derive(Error, Debug)]
pub enum EngineError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("Model inference error: {0}")]
    Model(String),
    #[error("Security error: {0}")]
    Security(String),
    #[error("Configuration error: {0}")]
    Config(String),
    #[error("Plugin error in '{plugin}': {message}")]
    Plugin { plugin: String, message: String },
}
