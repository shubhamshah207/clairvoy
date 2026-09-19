use clairvoy_core::models::{FileEntry, ImageCategory, MatchType};
use clairvoy_core::traits::MatcherPlugin;
use clairvoy_model::PerceptualHashBackend;
use clairvoy_plugins::{ExactHashMatcherPlugin, PhotoVisionMatcherPlugin};
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;
use std::sync::Arc;
use tempfile::tempdir;

#[test]
fn test_exact_hash_matcher() {
    let dir = tempdir().unwrap();
    let file1 = dir.path().join("a.bin");
    let file2 = dir.path().join("b.bin");
    let file3 = dir.path().join("c.bin");

    File::create(&file1)
        .unwrap()
        .write_all(b"identical byte payload")
        .unwrap();
    File::create(&file2)
        .unwrap()
        .write_all(b"identical byte payload")
        .unwrap();
    File::create(&file3)
        .unwrap()
        .write_all(b"completely different content")
        .unwrap();

    let files = vec![
        FileEntry {
            path: file1,
            size_bytes: 22,
            modified_epoch: 100,
            is_media: false,
            category: ImageCategory::File,
        },
        FileEntry {
            path: file2,
            size_bytes: 22,
            modified_epoch: 200,
            is_media: false,
            category: ImageCategory::File,
        },
        FileEntry {
            path: file3,
            size_bytes: 28,
            modified_epoch: 300,
            is_media: false,
            category: ImageCategory::File,
        },
    ];

    let matcher = ExactHashMatcherPlugin::new();
    let clusters = matcher.find_duplicates(&files, &files).unwrap();

    assert_eq!(clusters.len(), 1);
    assert_eq!(clusters[0].match_type, MatchType::ExactHash);
    assert_eq!(clusters[0].members.len(), 2);
}

#[test]
fn test_exact_hash_matcher_same_size_different_content() {
    let dir = tempdir().unwrap();
    let file1 = dir.path().join("same1.bin");
    let file2 = dir.path().join("same2.bin");

    // Both files have exactly 16 bytes, but different contents
    File::create(&file1)
        .unwrap()
        .write_all(b"12345678abcdefgh")
        .unwrap();
    File::create(&file2)
        .unwrap()
        .write_all(b"87654321hgfedcba")
        .unwrap();

    let files = vec![
        FileEntry {
            path: file1,
            size_bytes: 16,
            modified_epoch: 100,
            is_media: false,
            category: ImageCategory::File,
        },
        FileEntry {
            path: file2,
            size_bytes: 16,
            modified_epoch: 200,
            is_media: false,
            category: ImageCategory::File,
        },
    ];

    let matcher = ExactHashMatcherPlugin::new();
    let clusters = matcher.find_duplicates(&files, &files).unwrap();

    // Despite same size, distinct contents mean 0 duplicate clusters
    assert!(clusters.is_empty());
}

#[test]
fn test_exact_hash_matcher_zero_byte_direct() {
    let dir = tempdir().unwrap();
    let file1 = dir.path().join("zero1.bin");
    let file2 = dir.path().join("zero2.bin");

    File::create(&file1).unwrap().write_all(b"").unwrap();
    File::create(&file2).unwrap().write_all(b"").unwrap();

    let files = vec![
        FileEntry {
            path: file1,
            size_bytes: 0,
            modified_epoch: 100,
            is_media: false,
            category: ImageCategory::File,
        },
        FileEntry {
            path: file2,
            size_bytes: 0,
            modified_epoch: 200,
            is_media: false,
            category: ImageCategory::File,
        },
    ];

    let matcher = ExactHashMatcherPlugin::new();
    let clusters = matcher.find_duplicates(&files, &files).unwrap();
    // 0-byte files should never form duplicate clusters
    assert!(clusters.is_empty());
}

#[test]
fn test_exact_hash_matcher_metadata_and_filter() {
    let matcher = ExactHashMatcherPlugin::default();
    assert_eq!(matcher.plugin_id(), "exact_hash");
    assert_eq!(
        matcher.display_name(),
        "Byte-Exact Hash Matcher (BLAKE3 SIMD)"
    );
    assert_eq!(matcher.priority_order(), 10);
    assert_eq!(matcher.match_type(), MatchType::ExactHash);

    let files = vec![
        FileEntry {
            path: PathBuf::from("/test/empty.bin"),
            size_bytes: 0,
            modified_epoch: 1,
            is_media: false,
            category: ImageCategory::File,
        },
        FileEntry {
            path: PathBuf::from("/test/data.bin"),
            size_bytes: 100,
            modified_epoch: 2,
            is_media: false,
            category: ImageCategory::File,
        },
    ];

    let filtered = matcher.filter_supported(&files);
    assert_eq!(filtered.len(), 1);
    assert_eq!(filtered[0].size_bytes, 100);
}

#[test]
fn test_photo_vision_matcher_metadata() {
    let backend = Arc::new(PerceptualHashBackend::new());
    let plugin = PhotoVisionMatcherPlugin::new(backend.clone(), 0.85);

    assert_eq!(plugin.plugin_id(), "photo_vision");
    assert_eq!(
        plugin.display_name(),
        "Photo Vision Matcher (Pluggable Model)"
    );
    assert_eq!(plugin.priority_order(), 20);
    assert_eq!(plugin.match_type(), MatchType::VisualAiNearDuplicate);
    assert_eq!(plugin.threshold(), 0.85);
    assert_eq!(plugin.backend().model_id(), "perceptual_blockhash_64");

    let files = vec![
        FileEntry {
            path: PathBuf::from("/test/img.jpg"),
            size_bytes: 100,
            modified_epoch: 1,
            is_media: true,
            category: ImageCategory::Photo,
        },
        FileEntry {
            path: PathBuf::from("/test/doc.txt"),
            size_bytes: 50,
            modified_epoch: 2,
            is_media: false,
            category: ImageCategory::File,
        },
    ];

    let supported = plugin.filter_supported(&files);
    assert_eq!(supported.len(), 1);
    assert_eq!(supported[0].path, PathBuf::from("/test/img.jpg"));

    let duplicates = plugin.find_duplicates(&files, &files).unwrap();
    assert!(duplicates.is_empty());
}
