pub mod hasher;
pub mod walker;

pub use hasher::compute_quick_hash_4kb;
pub use walker::{
    scan_filesystem, scan_roots, scan_roots_with_progress, ScanStats, EXCLUDED_DIRS,
    SUPPORTED_IMAGE_EXTS, SUPPORTED_VIDEO_EXTS,
};
