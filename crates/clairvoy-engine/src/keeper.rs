use clairvoy_core::models::FileEntry;
use clairvoy_core::traits::KeeperStrategy;

pub struct CompositeKeeperStrategy;

impl CompositeKeeperStrategy {
    pub fn new() -> Self {
        Self
    }
}

impl Default for CompositeKeeperStrategy {
    fn default() -> Self {
        Self::new()
    }
}

impl KeeperStrategy for CompositeKeeperStrategy {
    fn score_entry(&self, entry: &FileEntry, _cluster: &[FileEntry]) -> i64 {
        let mut score = 100i64;
        let path_str = entry.path.to_string_lossy().to_lowercase();
        let fname = entry
            .path
            .file_name()
            .and_then(|f| f.to_str())
            .unwrap_or("")
            .to_lowercase();

        if path_str.contains("/trash/") || path_str.contains("/recycle") {
            score -= 500;
        }
        if fname.contains("copy") || fname.contains("-copy") {
            score -= 25;
        }
        if fname.contains("thumb") {
            score -= 50;
        }
        if fname.contains("edited") {
            score -= 10;
        }
        score
    }

    fn choose_keeper<'a>(&self, cluster: &'a [FileEntry]) -> (&'a FileEntry, Vec<&'a FileEntry>) {
        assert!(!cluster.is_empty(), "cluster cannot be empty");
        let mut scored: Vec<(&FileEntry, i64)> = cluster
            .iter()
            .map(|e| (e, self.score_entry(e, cluster)))
            .collect();
        scored.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.path.cmp(&b.0.path)));
        let keeper = scored[0].0;
        let duplicates = scored[1..].iter().map(|s| s.0).collect();
        (keeper, duplicates)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use clairvoy_core::models::ImageCategory;
    use std::path::PathBuf;

    fn make_entry(path: &str) -> FileEntry {
        FileEntry {
            path: PathBuf::from(path),
            size_bytes: 1024,
            modified_epoch: 1000,
            is_media: true,
            category: ImageCategory::Photo,
        }
    }

    #[test]
    fn test_score_entry_rules() {
        let strategy = CompositeKeeperStrategy::new();
        let normal = make_entry("/home/user/photos/photo.jpg");
        let copy = make_entry("/home/user/photos/photo - Copy.jpg");
        let thumb = make_entry("/home/user/photos/thumb_photo.jpg");
        let edited = make_entry("/home/user/photos/photo_edited.jpg");
        let trash = make_entry("/home/user/.local/share/trash/photo.jpg");

        assert_eq!(strategy.score_entry(&normal, &[]), 100);
        assert_eq!(strategy.score_entry(&copy, &[]), 75);
        assert_eq!(strategy.score_entry(&thumb, &[]), 50);
        assert_eq!(strategy.score_entry(&edited, &[]), 90);
        assert_eq!(strategy.score_entry(&trash, &[]), -400);
    }

    #[test]
    fn test_choose_keeper_prefers_original() {
        let strategy = CompositeKeeperStrategy::new();
        let normal = make_entry("/home/user/photos/IMG_0001.jpg");
        let copy = make_entry("/home/user/photos/IMG_0001 - Copy.jpg");

        let cluster = vec![copy.clone(), normal.clone()];
        let (keeper, dupes) = strategy.choose_keeper(&cluster);

        assert_eq!(keeper.path, normal.path);
        assert_eq!(dupes.len(), 1);
        assert_eq!(dupes[0].path, copy.path);
    }
}
