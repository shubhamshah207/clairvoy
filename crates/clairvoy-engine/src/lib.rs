pub mod keeper;
pub mod pipeline;
pub mod watcher;

pub use keeper::CompositeKeeperStrategy;
pub use pipeline::DeduplicationPipeline;
pub use watcher::AutonomousWatcher;
