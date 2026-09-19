use clairvoy_core::errors::EngineError;
use clairvoy_model::{ModelBackend, ModelRegistry, ModelsRegistryConfig, PerceptualHashBackend};
use image::{Rgb, RgbImage};
use tempfile::tempdir;

#[test]
fn test_perceptual_hash_backend() {
    let dir = tempdir().unwrap();
    let img_path1 = dir.path().join("test1.png");
    let img_path2 = dir.path().join("test2.png");

    let img = RgbImage::from_pixel(64, 64, Rgb([255, 0, 0]));
    img.save(&img_path1).unwrap();
    img.save(&img_path2).unwrap();

    let backend = PerceptualHashBackend::new();
    let emb1 = backend.embed_image(&img_path1).unwrap();
    let emb2 = backend.embed_image(&img_path2).unwrap();

    assert_eq!(emb1.len(), backend.embedding_dim());
    assert_eq!(emb1, emb2);
}

#[test]
fn test_perceptual_hash_backend_different_images() {
    let dir = tempdir().unwrap();
    let img_path_red = dir.path().join("red.png");
    let img_path_pattern = dir.path().join("pattern.png");

    let red = RgbImage::from_pixel(64, 64, Rgb([255, 0, 0]));
    red.save(&img_path_red).unwrap();

    let mut pattern = RgbImage::new(64, 64);
    for x in 0..64 {
        for y in 0..64 {
            if (x / 8 + y / 8) % 2 == 0 {
                pattern.put_pixel(x, y, Rgb([255, 255, 255]));
            } else {
                pattern.put_pixel(x, y, Rgb([0, 0, 0]));
            }
        }
    }
    pattern.save(&img_path_pattern).unwrap();

    let backend = PerceptualHashBackend::default();
    let emb_red = backend.embed_image(&img_path_red).unwrap();
    let emb_pattern = backend.embed_image(&img_path_pattern).unwrap();

    assert_eq!(emb_red.len(), 64);
    assert_eq!(emb_pattern.len(), 64);
    assert_ne!(emb_red, emb_pattern);
}

#[test]
fn test_perceptual_hash_backend_missing_file() {
    let dir = tempdir().unwrap();
    let missing_path = dir.path().join("does_not_exist.png");

    let backend = PerceptualHashBackend::new();
    let res = backend.embed_image(&missing_path);

    assert!(res.is_err());
    match res {
        Err(EngineError::Model(msg)) => {
            assert!(msg.contains("Image decode error"));
        }
        other => panic!("Expected EngineError::Model, got {:?}", other),
    }
}

#[test]
fn test_perceptual_hash_backend_metadata() {
    let backend = PerceptualHashBackend::new();
    assert_eq!(backend.model_id(), "perceptual_blockhash_64");
    assert_eq!(backend.embedding_dim(), 64);
}

#[test]
fn test_models_registry_config_parse_and_create_backend() {
    let toml_content = r#"
default_model = "fast_hash"

[models.fast_hash]
backend = "perceptual"
embedding_dim = 64
input_size = [64, 64]

[models.dinov2_vitb14]
backend = "onnx"
model_path = "/models/dinov2.onnx"
embedding_dim = 768
input_size = [224, 224]
"#;

    let registry = ModelRegistry::from_toml_str(toml_content).unwrap();
    assert_eq!(registry.config.default_model, "fast_hash");
    assert_eq!(registry.config.models.len(), 2);

    let default_backend = registry.create_backend(None).unwrap();
    assert_eq!(default_backend.model_id(), "perceptual_blockhash_64");
    assert_eq!(default_backend.embedding_dim(), 64);

    let named_backend = registry.create_backend(Some("fast_hash")).unwrap();
    assert_eq!(named_backend.model_id(), "perceptual_blockhash_64");

    // Unsupported backend should return error
    let onnx_res = registry.create_backend(Some("dinov2_vitb14"));
    match onnx_res {
        Err(EngineError::Config(msg)) => {
            assert!(msg.contains("Unsupported model backend 'onnx'"));
        }
        _ => panic!("Expected EngineError::Config"),
    }

    // Unknown model should return error
    let unknown_res = registry.create_backend(Some("non_existent_model"));
    match unknown_res {
        Err(EngineError::Config(msg)) => {
            assert!(msg.contains("Model 'non_existent_model' not found in registry"));
        }
        _ => panic!("Expected EngineError::Config"),
    }
}

#[test]
fn test_models_registry_load_file_and_invalid_toml() {
    let dir = tempdir().unwrap();
    let config_path = dir.path().join("models.toml");

    let toml_content = r#"
default_model = "perceptual"
"#;
    std::fs::write(&config_path, toml_content).unwrap();

    let registry = ModelRegistry::load_from_file(&config_path).unwrap();
    assert_eq!(registry.config.default_model, "perceptual");
    let backend = registry.create_backend(None).unwrap();
    assert_eq!(backend.model_id(), "perceptual_blockhash_64");

    let bad_config = dir.path().join("bad.toml");
    std::fs::write(&bad_config, "NOT VALID TOML :::").unwrap();
    assert!(ModelsRegistryConfig::load_from_file(&bad_config).is_err());
}
