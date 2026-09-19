use clairvoy_core::errors::EngineError;
use clairvoy_core::models::{FileEntry, ImageCategory};
use jwalk::WalkDirGeneric;
use std::collections::HashSet;
use std::io;
use std::path::PathBuf;

pub const SUPPORTED_IMAGE_EXTS: &[&str] = &[
    "jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif", "heic", "heif", "psd",
];
pub const SUPPORTED_VIDEO_EXTS: &[&str] = &[
    "mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "ts", "mp",
];

pub const EXCLUDED_DIRS: &[&str] = &[
    ".git",
    ".svn",
    "node_modules",
    "__pycache__",
    ".cache",
    "_duplicate_quarantine",
    "_dedupe_reports",
    "_logs",
    "_zips",
    ".vscode",
    ".idea",
    "$RECYCLE.BIN",
    "System Volume Information",
    ".venv",
    "venv",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct ScanStats {
    pub total_files: usize,
    pub media_files: usize,
}

fn convert_dir_entry(entry: jwalk::DirEntry<((), ())>) -> Option<FileEntry> {
    if !entry.file_type.is_file() {
        return None;
    }

    // Gracefully skip files with unreadable metadata (e.g. PermissionDenied, NotFound)
    let Ok(metadata) = entry.metadata() else {
        return None;
    };

    let size_bytes = metadata.len();
    if size_bytes == 0 {
        return None;
    }

    let path = entry.path();
    let ext = path
        .extension()
        .and_then(|s| s.to_str())
        .unwrap_or("")
        .to_lowercase();
    let is_image = SUPPORTED_IMAGE_EXTS.contains(&ext.as_str());
    let is_video = SUPPORTED_VIDEO_EXTS.contains(&ext.as_str());
    let is_media = is_image || is_video;

    let category = if is_video {
        ImageCategory::Video
    } else if is_image {
        ImageCategory::Photo
    } else {
        ImageCategory::File
    };

    let modified_epoch = metadata
        .modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_secs())
        .unwrap_or(0);

    Some(FileEntry {
        path,
        size_bytes,
        modified_epoch,
        is_media,
        category,
    })
}

pub fn scan_roots(roots: &[PathBuf]) -> Result<(Vec<FileEntry>, usize), io::Error> {
    for root in roots {
        if !root.exists() {
            return Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Scan root does not exist: {}", root.display()),
            ));
        }
    }

    let mut entries = Vec::new();
    let mut media_count = 0;
    let excluded: HashSet<&str> = EXCLUDED_DIRS.iter().copied().collect();

    for root in roots {
        let excluded_filter = excluded.clone();
        let walker = WalkDirGeneric::<((), ())>::new(root)
            .skip_hidden(false)
            .process_read_dir(move |_depth, _path, _state, children| {
                children.retain(|dir_entry_result| {
                    dir_entry_result
                        .as_ref()
                        .map(|de| {
                            let name = de.file_name.to_string_lossy();
                            !excluded_filter.contains(name.as_ref())
                        })
                        .unwrap_or(false)
                });
            });

        for entry in walker.into_iter().flatten() {
            if let Some(file_entry) = convert_dir_entry(entry) {
                if file_entry.is_media {
                    media_count += 1;
                }
                entries.push(file_entry);
            }
        }
    }

    Ok((entries, media_count))
}

pub fn scan_filesystem(
    roots: &[PathBuf],
    sender: flume::Sender<FileEntry>,
) -> Result<ScanStats, EngineError> {
    for root in roots {
        if !root.exists() {
            return Err(EngineError::Io(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Scan root does not exist: {}", root.display()),
            )));
        }
    }

    let mut stats = ScanStats::default();
    let excluded: HashSet<&str> = EXCLUDED_DIRS.iter().copied().collect();

    for root in roots {
        let excluded_filter = excluded.clone();
        let walker = WalkDirGeneric::<((), ())>::new(root)
            .skip_hidden(false)
            .process_read_dir(move |_depth, _path, _state, children| {
                children.retain(|dir_entry_result| {
                    dir_entry_result
                        .as_ref()
                        .map(|de| {
                            let name = de.file_name.to_string_lossy();
                            !excluded_filter.contains(name.as_ref())
                        })
                        .unwrap_or(false)
                });
            });

        for entry in walker.into_iter().flatten() {
            if let Some(file_entry) = convert_dir_entry(entry) {
                stats.total_files += 1;
                if file_entry.is_media {
                    stats.media_files += 1;
                }
                if sender.send(file_entry).is_err() {
                    return Ok(stats);
                }
            }
        }
    }

    Ok(stats)
}
