use clairvoy_core::models::{ActionType, ImageCategory};
use clairvoy_engine::keeper::CompositeKeeperStrategy;
use clairvoy_engine::pipeline::DeduplicationPipeline;
use clairvoy_plugins::ExactHashMatcherPlugin;
use std::fs::File;
use std::io::Write;
use std::sync::Arc;
use tempfile::tempdir;

#[test]
fn test_deduplication_pipeline_runs_and_scores_keeper() {
    let dir = tempdir().unwrap();
    let original = dir.path().join("IMG_1001.jpg");
    let copy = dir.path().join("IMG_1001 - Copy.jpg");

    File::create(&original)
        .unwrap()
        .write_all(b"duplicate photo payload")
        .unwrap();
    File::create(&copy)
        .unwrap()
        .write_all(b"duplicate photo payload")
        .unwrap();

    let mut pipeline = DeduplicationPipeline::new(vec![dir.path().to_path_buf()]);
    pipeline.register_matcher(Arc::new(ExactHashMatcherPlugin::new()));
    pipeline.set_keeper_strategy(Arc::new(CompositeKeeperStrategy::new()));

    let summary = pipeline.run(|_stage, _cur, _tot| {}).unwrap();
    assert_eq!(summary.total_duplicate_groups, 1);
    assert_eq!(summary.groups.len(), 2);

    let keep_rec = summary
        .groups
        .iter()
        .find(|r| r.action == ActionType::Keep)
        .unwrap();
    assert!(keep_rec.path.contains("IMG_1001.jpg") && !keep_rec.path.contains("- Copy"));
    assert_eq!(keep_rec.category, ImageCategory::Photo);
}

#[test]
fn test_deduplication_pipeline_sequential_group_ids() {
    let dir = tempdir().unwrap();
    // Cluster 1
    File::create(dir.path().join("a1.jpg"))
        .unwrap()
        .write_all(b"payload_group_one")
        .unwrap();
    File::create(dir.path().join("a2.jpg"))
        .unwrap()
        .write_all(b"payload_group_one")
        .unwrap();

    // Cluster 2
    File::create(dir.path().join("b1.png"))
        .unwrap()
        .write_all(b"payload_group_two_different")
        .unwrap();
    File::create(dir.path().join("b2.png"))
        .unwrap()
        .write_all(b"payload_group_two_different")
        .unwrap();

    let mut pipeline = DeduplicationPipeline::new(vec![dir.path().to_path_buf()]);
    pipeline.register_matcher(Arc::new(ExactHashMatcherPlugin::new()));
    pipeline.set_keeper_strategy(Arc::new(CompositeKeeperStrategy::new()));

    let summary = pipeline.run(|_stage, _cur, _tot| {}).unwrap();
    assert_eq!(summary.total_duplicate_groups, 2);
    assert_eq!(summary.groups.len(), 4);

    let group_ids: std::collections::HashSet<usize> =
        summary.groups.iter().map(|r| r.group_id).collect();
    assert!(group_ids.contains(&1));
    assert!(group_ids.contains(&2));
    assert_eq!(group_ids.len(), 2);
}
