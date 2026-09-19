use clairvoy_core::models::ImageCategory;
use clairvoy_scanner::{compute_quick_hash_4kb, scan_filesystem, scan_roots};
use std::fs::{self, File};
use std::io::Write;
use tempfile::tempdir;

#[test]
fn test_scanner_discovers_and_quick_hashes() {
    let dir = tempdir().unwrap();
    let file1 = dir.path().join("photo1.jpg");
    let file2 = dir.path().join("photo2.jpg");

    let mut f1 = File::create(&file1).unwrap();
    f1.write_all(b"Hello World quick hash test content")
        .unwrap();

    let mut f2 = File::create(&file2).unwrap();
    f2.write_all(b"Hello World quick hash test content")
        .unwrap();

    let h1 = compute_quick_hash_4kb(&file1).unwrap();
    let h2 = compute_quick_hash_4kb(&file2).unwrap();
    assert_eq!(h1, h2);

    let (entries, media_count) = scan_roots(&[dir.path().to_path_buf()]).unwrap();
    assert_eq!(entries.len(), 2);
    assert_eq!(media_count, 2);
}

#[test]
fn test_quick_hash_properties() {
    let dir = tempdir().unwrap();
    let file1 = dir.path().join("file1.bin");
    let file2 = dir.path().join("file2.bin");
    let file3 = dir.path().join("file3.bin");

    // file1: 8KB of 0xAA
    let mut f1 = File::create(&file1).unwrap();
    let mut data1 = vec![0xAAu8; 8192];
    f1.write_all(&data1).unwrap();

    // file2: same first 4KB of 0xAA, but different second 4KB of 0xBB
    let mut f2 = File::create(&file2).unwrap();
    let mut data2 = vec![0xAAu8; 4096];
    data2.extend_from_slice(&[0xBBu8; 4096]);
    f2.write_all(&data2).unwrap();

    // file3: different first byte
    let mut f3 = File::create(&file3).unwrap();
    data1[0] = 0x00;
    f3.write_all(&data1).unwrap();

    let h1 = compute_quick_hash_4kb(&file1).unwrap();
    let h2 = compute_quick_hash_4kb(&file2).unwrap();
    let h3 = compute_quick_hash_4kb(&file3).unwrap();

    // h1 and h2 match because quick hash only reads the first 4KB
    assert_eq!(h1, h2);
    // h3 differs because first byte changed
    assert_ne!(h1, h3);
}

#[test]
fn test_scanner_excludes_and_categories() {
    let dir = tempdir().unwrap();

    // Normal files
    let photo = dir.path().join("pic.jpg");
    File::create(&photo)
        .unwrap()
        .write_all(b"photo content")
        .unwrap();

    let video = dir.path().join("movie.mp4");
    File::create(&video)
        .unwrap()
        .write_all(b"video content")
        .unwrap();

    let doc = dir.path().join("notes.txt");
    File::create(&doc)
        .unwrap()
        .write_all(b"plain text")
        .unwrap();

    // Zero-byte file: should be skipped
    let empty = dir.path().join("empty.png");
    File::create(&empty).unwrap();

    // Excluded directory files: should be skipped
    let git_dir = dir.path().join(".git");
    fs::create_dir_all(&git_dir).unwrap();
    File::create(git_dir.join("head_commit.jpg"))
        .unwrap()
        .write_all(b"git photo")
        .unwrap();

    let node_dir = dir.path().join("node_modules");
    fs::create_dir_all(&node_dir).unwrap();
    File::create(node_dir.join("package_icon.png"))
        .unwrap()
        .write_all(b"pkg icon")
        .unwrap();

    let (entries, media_count) = scan_roots(&[dir.path().to_path_buf()]).unwrap();
    assert_eq!(
        entries.len(),
        3,
        "Expected exactly 3 valid non-empty, non-excluded files"
    );
    assert_eq!(media_count, 2, "Expected 2 media files (photo + video)");

    let photo_entry = entries.iter().find(|e| e.path == photo).unwrap();
    assert_eq!(photo_entry.category, ImageCategory::Photo);
    assert!(photo_entry.is_media);

    let video_entry = entries.iter().find(|e| e.path == video).unwrap();
    assert_eq!(video_entry.category, ImageCategory::Video);
    assert!(video_entry.is_media);

    let doc_entry = entries.iter().find(|e| e.path == doc).unwrap();
    assert_eq!(doc_entry.category, ImageCategory::File);
    assert!(!doc_entry.is_media);
}

#[test]
fn test_scan_filesystem_bounded_streaming() {
    let dir = tempdir().unwrap();

    for i in 0..10 {
        let file = dir.path().join(format!("image_{}.png", i));
        File::create(&file)
            .unwrap()
            .write_all(b"image bytes")
            .unwrap();
    }

    let (tx, rx) = flume::bounded(2048);
    let roots = vec![dir.path().to_path_buf()];

    let stats = scan_filesystem(&roots, tx).unwrap();
    assert_eq!(stats.total_files, 10);
    assert_eq!(stats.media_files, 10);

    let mut received = Vec::new();
    while let Ok(entry) = rx.try_recv() {
        received.push(entry);
    }
    assert_eq!(received.len(), 10);
}

#[test]
fn test_scan_filesystem_receiver_dropped() {
    let dir = tempdir().unwrap();

    for i in 0..20 {
        let file = dir.path().join(format!("image_{}.png", i));
        File::create(&file)
            .unwrap()
            .write_all(b"image bytes")
            .unwrap();
    }

    // Capacity of 2 entries
    let (tx, rx) = flume::bounded(2);
    let roots = vec![dir.path().to_path_buf()];

    // Drop the receiver immediately
    drop(rx);

    // scan_filesystem should gracefully stop and not crash
    let res = scan_filesystem(&roots, tx);
    assert!(res.is_ok());
}
