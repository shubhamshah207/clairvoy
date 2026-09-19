pub mod routes;
pub mod state;

pub use routes::{
    build_router, build_router_full, build_router_with_services, build_router_with_state,
    handle_duplicates, handle_index, handle_runs, handle_scan, handle_status,
    handle_status_stream, handle_watch_daemon_toggle, handle_watch_paths_add,
    handle_watch_paths_delete, handle_watch_paths_list, handle_watch_paths_toggle,
    DaemonTogglePayload, DuplicatesQuery, ScanPayload, WatchPathPayload, WatchTogglePayload,
};
pub use state::{AppScanState, ServerState, SharedScanState};

