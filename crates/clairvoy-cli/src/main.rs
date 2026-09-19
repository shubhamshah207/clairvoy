pub mod progress;

use clap::{Parser, Subcommand};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

#[derive(Parser, Debug)]
#[command(name = "clairvoy-rs", version = "0.2.0", about = "Pure Rust High-Performance Deduplication Engine")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug, PartialEq, Eq)]
pub enum Commands {
    /// Scan one or more directories for duplicate files with real-time terminal progress
    Scan {
        #[arg(required = true)]
        paths: Vec<PathBuf>,
        /// Optional Clairvoy UI server URL to coordinate scan through active web server
        #[arg(long)]
        server: Option<String>,
    },
    /// Inspect status or follow live SSE progress stream from a running Clairvoy server
    Status {
        /// Clairvoy server base URL
        #[arg(short, long, default_value = "http://127.0.0.1:8000")]
        server: String,
        /// Follow live SSE progress stream in real time with animated progress bar
        #[arg(short, long)]
        follow: bool,
    },
    /// Clean duplicate files with transparent, chunked terminal progress
    Clean {
        /// Clairvoy server base URL
        #[arg(short, long, default_value = "http://127.0.0.1:8000")]
        server: String,
        /// Clean 100% byte-exact duplicates only (preserves all primary keeper files)
        #[arg(long, default_value_t = true)]
        exact: bool,
        /// Deletion mode: trash, permanent, or hardlink
        #[arg(long, default_value = "trash")]
        mode: String,
    },
    /// Launch the web dashboard server
    Ui {
        #[arg(short, long, default_value = "8000")]
        port: u16,
        #[arg(long, default_value = "0.0.0.0")]
        host: String,
        /// Disable autonomous background filesystem watcher daemon
        #[arg(long)]
        no_daemon: bool,
        /// Watcher sliding debounce quiet window in milliseconds
        #[arg(long, default_value = "1000")]
        debounce_ms: u64,
        /// Watcher fallback periodic scan interval in seconds (0 to disable)
        #[arg(long, default_value = "3600")]
        fallback_interval: u64,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Scan { paths, server } => {
            if let Some(server_url) = server {
                println!("[*] Coordinating scan across {} path(s) via Clairvoy Server ({}) ...", paths.len(), server_url);
                let client = reqwest::Client::new();
                let scan_ep = format!("{}/api/scan", server_url.trim_end_matches('/'));
                let payload = serde_json::json!({
                    "paths": paths.iter().map(|p| p.to_string_lossy().to_string()).collect::<Vec<_>>(),
                    "enable_ml": true,
                    "threshold": 0.9,
                });
                let res = client.post(&scan_ep).json(&payload).send().await?;
                if !res.status().is_success() {
                    let err_txt = res.text().await.unwrap_or_else(|_| "Unknown error".to_string());
                    eprintln!("[✗] Server rejected scan request: {}", err_txt);
                    return Ok(());
                }
                println!("[*] Scan triggered successfully on server. Streaming real-time progress...");
                stream_server_progress(&server_url).await?;
            } else {
                println!("[*] Initializing Clairvoy Pure Rust Engine across {} path(s)...", paths.len());
                let mut pipeline = clairvoy_engine::DeduplicationPipeline::new(paths);
                pipeline.register_matcher(Arc::new(clairvoy_plugins::ExactHashMatcherPlugin::new()));

                let mut pb = progress::TerminalProgressBar::new("Initializing filesystem scan", 0);
                let summary = pipeline.run(|stage, cur, tot| {
                    if tot > 0 {
                        pb.set_total(tot);
                    }
                    pb.update(cur, stage);
                })?;

                pb.finish(&format!(
                    "Scan complete: {} files analyzed in {:.2}s. Discovered {} duplicate groups ({:.3} GB / {:.1} MB recoverable).",
                    summary.total_files_scanned, summary.duration_seconds, summary.total_duplicate_groups, summary.wasted_gb, summary.wasted_mb
                ));
            }
        }
        Commands::Status { server, follow } => {
            if follow {
                stream_server_progress(&server).await?;
            } else {
                let status_url = format!("{}/api/status", server.trim_end_matches('/'));
                let client = reqwest::Client::new();
                let res = client.get(&status_url).send().await?;
                if !res.status().is_success() {
                    eprintln!("[✗] Failed to fetch server status: HTTP {}", res.status());
                    return Ok(());
                }
                let val: serde_json::Value = res.json().await?;
                println!("+-------------------------------------------------------------+");
                println!("|                 CLAIRVOY SERVER STATUS                      |");
                println!("+-------------------------------------------------------------+");
                println!("  Server URL:         {}", server);
                println!("  Lifecycle Status:   {}", val.get("status").and_then(|v| v.as_str()).unwrap_or("unknown"));
                println!("  Current Stage:      {}", val.get("stage").and_then(|v| v.as_str()).unwrap_or("-"));
                println!("  Progress:           {}%", val.get("progress_pct").and_then(|v| v.as_u64()).unwrap_or(0));
                println!("  Files Indexed:      {}", val.get("files_indexed").and_then(|v| v.as_u64()).unwrap_or(0));
                println!("  Recoverable Space:  {:.2} GB ({:.1} MB)",
                    val.get("wasted_gb").and_then(|v| v.as_f64()).unwrap_or(0.0),
                    val.get("wasted_mb").and_then(|v| v.as_f64()).unwrap_or(0.0)
                );
                if let Some(run_id) = val.get("run_id").and_then(|v| v.as_str()) {
                    println!("  Active Scan Run:    {}", run_id);
                }
                if let Some(msg) = val.get("message").and_then(|v| v.as_str()) {
                    println!("  Message:            {}", msg);
                }

                // Check watched paths
                let watch_url = format!("{}/api/watch/paths", server.trim_end_matches('/'));
                if let Ok(watch_res) = client.get(&watch_url).send().await {
                    if let Ok(watch_list) = watch_res.json::<Vec<serde_json::Value>>().await {
                        println!("+-------------------------------------------------------------+");
                        println!("|  SURVEILLANCE WATCHED DIRECTORIES                           |");
                        println!("+-------------------------------------------------------------+");
                        if watch_list.is_empty() {
                            println!("  (No watched folders configured)");
                        } else {
                            for w in watch_list {
                                let id = w.get("id").and_then(|v| v.as_i64()).unwrap_or(0);
                                let p = w.get("path").and_then(|v| v.as_str()).unwrap_or("");
                                let en = w.get("enabled").and_then(|v| v.as_i64()).unwrap_or(0) == 1;
                                println!("  [{}] {} (Status: {})", id, p, if en { "ACTIVE" } else { "PAUSED" });
                            }
                        }
                    }
                }
                println!("+-------------------------------------------------------------+");
            }
        }
        Commands::Clean { server, exact, mode } => {
            let status_url = format!("{}/api/status", server.trim_end_matches('/'));
            let client = reqwest::Client::new();
            let res = client.get(&status_url).send().await?;
            if !res.status().is_success() {
                eprintln!("[✗] Failed to fetch server status: HTTP {}", res.status());
                return Ok(());
            }
            let val: serde_json::Value = res.json().await?;
            let summary = val.get("summary");
            let groups = summary.and_then(|s| s.get("groups")).and_then(|g| g.as_array());

            let mut targets = Vec::new();
            let mut total_bytes: u64 = 0;
            if let Some(group_items) = groups {
                for it in group_items {
                    let action = it.get("action").and_then(|v| v.as_str()).unwrap_or("");
                    let match_type = it.get("match_type").and_then(|v| v.as_str()).unwrap_or("");
                    if action == "DUPLICATE" && (!exact || match_type == "ExactHash" || match_type == "EXACT_HASH") {
                        if let Some(p) = it.get("path").and_then(|v| v.as_str()) {
                            targets.push(p.to_string());
                            let size_mb = it.get("size_mb").and_then(|v| v.as_f64()).unwrap_or(0.0);
                            total_bytes += (size_mb * 1024.0 * 1024.0) as u64;
                        }
                    }
                }
            }

            if targets.is_empty() {
                println!("[✓] No candidate duplicate files found to clean.");
                return Ok(());
            }

            let total_gb = total_bytes as f64 / (1024.0 * 1024.0 * 1024.0);
            println!(
                "[*] Found {} duplicate files ({:.2} GB). Cleaning in chunks of 150 (mode: {})...",
                targets.len(), total_gb, mode
            );

            let chunk_size = 150;
            let mut pb = progress::TerminalProgressBar::new(&format!("Batch {}", mode), targets.len());
            let mut total_freed_files = 0;
            let mut total_freed_bytes: u64 = 0;

            let delete_ep = format!("{}/api/delete/execute", server.trim_end_matches('/'));
            for (idx, chunk) in targets.chunks(chunk_size).enumerate() {
                let current_processed = idx * chunk_size + chunk.len();
                pb.update(
                    current_processed,
                    &format!("Cleaning batch {}/{} ({:.2} MB freed)", idx + 1, targets.len().div_ceil(chunk_size), total_freed_bytes as f64 / 1_048_576.0)
                );

                let payload = serde_json::json!({
                    "paths": chunk,
                    "mode": mode,
                });

                let del_res = client.post(&delete_ep).json(&payload).send().await?;
                if del_res.status().is_success() {
                    let res_body: serde_json::Value = del_res.json().await?;
                    let freed = res_body.get("total_files_freed")
                        .or_else(|| res_body.get("total_files_deleted"))
                        .and_then(|v| v.as_u64())
                        .unwrap_or(chunk.len() as u64) as usize;
                    let bytes = res_body.get("total_bytes_freed").and_then(|v| v.as_u64()).unwrap_or(0);
                    total_freed_files += freed;
                    total_freed_bytes += bytes;
                }
            }

            pb.finish(&format!(
                "Batch clean complete: {} files processed in {} mode ({:.2} MB / {:.3} GB freed).",
                total_freed_files, mode, total_freed_bytes as f64 / 1_048_576.0, total_freed_bytes as f64 / 1_073_741_824.0
            ));
        }
        Commands::Ui {
            port,
            host,
            no_daemon,
            debounce_ms,
            fallback_interval,
        } => {
            let addr: SocketAddr = format!("{}:{}", host, port).parse()?;
            let db = Arc::new(Mutex::new(clairvoy_core::db::Database::open(None)?));

            let scan_state: clairvoy_server::SharedScanState = Default::default();
            if let Ok(db_guard) = db.lock() {
                clairvoy_server::routes::auto_load_recent_run_with_db(&scan_state, Some(&db_guard));
            }

            let watcher = if no_daemon {
                println!("[*] Autonomous watcher daemon disabled (--no-daemon). On-the-fly scanning remains 100% active.");
                None
            } else {
                println!(
                    "[*] Starting Autonomous Watcher daemon (debounce: {}ms, fallback interval: {}s)...",
                    debounce_ms, fallback_interval
                );
                let scan_state_cb = Arc::clone(&scan_state);
                let progress_cb = Arc::new(move |stage: &str, cur: usize, tot: usize| {
                    if let Ok(mut s) = scan_state_cb.lock() {
                        if stage == "Scan complete" {
                            s.status = "completed".to_string();
                            s.stage = "Scan complete".to_string();
                            s.progress_pct = 100;
                            s.files_indexed = cur;
                            s.message = format!("Surveillance scan complete: {} files indexed", cur);
                        } else {
                            s.status = "running".to_string();
                            s.stage = stage.to_string();
                            s.progress_pct = if tot > 0 {
                                ((cur as f64 / tot as f64) * 100.0).min(100.0) as u32
                            } else if cur > 0 {
                                ((cur as f64).log10() * 18.0).min(85.0) as u32
                            } else {
                                0
                            };
                            s.files_indexed = cur;
                            s.message = format!("{}: {} / {}", stage, cur, tot);
                        }
                    }
                });

                let w = clairvoy_engine::AutonomousWatcher::start_with_progress(
                    Arc::clone(&db),
                    debounce_ms,
                    fallback_interval,
                    Some(progress_cb),
                )
                .await?;
                Some(Arc::new(w))
            };

            let listener = if host == "0.0.0.0" {
                // Dual-stack bind [::]:port so Windows host browser can connect via localhost (::1 and 127.0.0.1)
                match tokio::net::TcpListener::bind(format!("[::]:{}", port)).await {
                    Ok(l) => {
                        println!("[*] Starting Clairvoy Rust Web Server at http://localhost:{} (dual-stack [::]:{}) ...", port, port);
                        l
                    }
                    Err(_) => {
                        println!("[*] Starting Clairvoy Rust Web Server at http://{}:{} ...", host, port);
                        tokio::net::TcpListener::bind(addr).await?
                    }
                }
            } else {
                println!("[*] Starting Clairvoy Rust Web Server at http://{}:{} ...", host, port);
                tokio::net::TcpListener::bind(addr).await?
            };

            let app = clairvoy_server::build_router_with_services(scan_state, db, watcher);
            axum::serve(listener, app).await?;
        }
    }

    Ok(())
}

async fn stream_server_progress(server_url: &str) -> Result<(), Box<dyn std::error::Error>> {
    let stream_url = format!("{}/api/status/stream", server_url.trim_end_matches('/'));
    println!("[*] Connecting to live SSE status stream at {}...", stream_url);

    let client = reqwest::Client::new();
    let mut res = client.get(&stream_url).send().await?;
    if !res.status().is_success() {
        return Err(format!("Failed to connect to status stream: HTTP {}", res.status()).into());
    }

    let mut pb = progress::TerminalProgressBar::new("Surveillance / Scan Progress", 0);
    let mut buffer = String::new();

    while let Some(chunk) = res.chunk().await? {
        buffer.push_str(&String::from_utf8_lossy(&chunk));

        while let Some(newline_pos) = buffer.find('\n') {
            let line = buffer[..newline_pos].trim().to_string();
            buffer = buffer[newline_pos + 1..].to_string();

            if let Some(json_str) = line.strip_prefix("data:") {
                let json_str = json_str.trim();
                if json_str.is_empty() {
                    continue;
                }
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(json_str) {
                    let status = val.get("status").and_then(|v| v.as_str()).unwrap_or("idle");
                    let stage = val.get("stage").and_then(|v| v.as_str()).unwrap_or("");
                    let message = val.get("message").and_then(|v| v.as_str()).unwrap_or("");
                    let files_indexed = val.get("files_indexed").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
                    let pct = val.get("progress_pct").and_then(|v| v.as_u64()).unwrap_or(0) as usize;

                    if status == "running" {
                        pb.set_total(100);
                        let display_msg = if !message.is_empty() { message } else { stage };
                        pb.update(pct, display_msg);
                    } else if status == "completed" {
                        let wasted_gb = val.get("wasted_gb").and_then(|v| v.as_f64()).unwrap_or(0.0);
                        let wasted_mb = val.get("wasted_mb").and_then(|v| v.as_f64()).unwrap_or(0.0);
                        pb.finish(&format!(
                            "Scan completed: {} files indexed ({:.2} MB / {:.3} GB recoverable space)",
                            files_indexed, wasted_mb, wasted_gb
                        ));
                        return Ok(());
                    } else if status == "failed" {
                        let err = val.get("error").and_then(|v| v.as_str()).unwrap_or(message);
                        pb.fail(err);
                        return Ok(());
                    } else if status == "idle" {
                        pb.render("Server is idle (surveillance monitoring active)");
                    }
                }
            }
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cli_parse_scan() {
        let args = vec!["clairvoy-rs", "scan", "/tmp/dir1", "/tmp/dir2"];
        let cli = Cli::try_parse_from(args).expect("Should parse scan command");
        match cli.command {
            Commands::Scan { paths, server } => {
                assert_eq!(paths.len(), 2);
                assert_eq!(paths[0], PathBuf::from("/tmp/dir1"));
                assert_eq!(paths[1], PathBuf::from("/tmp/dir2"));
                assert!(server.is_none());
            }
            _ => panic!("Expected Commands::Scan"),
        }
    }

    #[test]
    fn test_cli_parse_scan_with_server() {
        let args = vec!["clairvoy-rs", "scan", "/tmp/dir1", "--server", "http://localhost:8000"];
        let cli = Cli::try_parse_from(args).expect("Should parse scan command with server");
        match cli.command {
            Commands::Scan { paths, server } => {
                assert_eq!(paths.len(), 1);
                assert_eq!(server.as_deref(), Some("http://localhost:8000"));
            }
            _ => panic!("Expected Commands::Scan"),
        }
    }

    #[test]
    fn test_cli_parse_status() {
        let args = vec!["clairvoy-rs", "status", "--follow", "--server", "http://127.0.0.1:9000"];
        let cli = Cli::try_parse_from(args).expect("Should parse status command");
        match cli.command {
            Commands::Status { server, follow } => {
                assert_eq!(server, "http://127.0.0.1:9000");
                assert!(follow);
            }
            _ => panic!("Expected Commands::Status"),
        }
    }

    #[test]
    fn test_cli_parse_clean() {
        let args = vec!["clairvoy-rs", "clean", "--exact", "--mode", "hardlink"];
        let cli = Cli::try_parse_from(args).expect("Should parse clean command");
        match cli.command {
            Commands::Clean { server, exact, mode } => {
                assert_eq!(server, "http://127.0.0.1:8000");
                assert!(exact);
                assert_eq!(mode, "hardlink");
            }
            _ => panic!("Expected Commands::Clean"),
        }
    }

    #[test]
    fn test_cli_parse_ui_defaults() {
        let args = vec!["clairvoy-rs", "ui"];
        let cli = Cli::try_parse_from(args).expect("Should parse ui command defaults");
        match cli.command {
            Commands::Ui {
                port,
                host,
                no_daemon,
                debounce_ms,
                fallback_interval,
            } => {
                assert_eq!(port, 8000);
                assert_eq!(host, "0.0.0.0");
                assert!(!no_daemon);
                assert_eq!(debounce_ms, 1000);
                assert_eq!(fallback_interval, 3600);
            }
            _ => panic!("Expected Commands::Ui"),
        }
    }

    #[test]
    fn test_cli_parse_ui_custom_args() {
        let args = vec!["clairvoy-rs", "ui", "--port", "9090", "--host", "127.0.0.1"];
        let cli = Cli::try_parse_from(args).expect("Should parse custom ui arguments");
        match cli.command {
            Commands::Ui {
                port,
                host,
                no_daemon,
                debounce_ms,
                fallback_interval,
            } => {
                assert_eq!(port, 9090);
                assert_eq!(host, "127.0.0.1");
                assert!(!no_daemon);
                assert_eq!(debounce_ms, 1000);
                assert_eq!(fallback_interval, 3600);
            }
            _ => panic!("Expected Commands::Ui"),
        }
    }

    #[test]
    fn test_cli_parse_ui_no_daemon() {
        let args = vec!["clairvoy-rs", "ui", "--no-daemon"];
        let cli = Cli::try_parse_from(args).expect("Should parse ui --no-daemon");
        match cli.command {
            Commands::Ui { no_daemon, .. } => {
                assert!(no_daemon);
            }
            _ => panic!("Expected Commands::Ui"),
        }
    }

    #[test]
    fn test_cli_parse_ui_custom_watcher_flags() {
        let args = vec![
            "clairvoy-rs",
            "ui",
            "--debounce-ms",
            "500",
            "--fallback-interval",
            "1800",
        ];
        let cli = Cli::try_parse_from(args).expect("Should parse custom watcher flags");
        match cli.command {
            Commands::Ui {
                debounce_ms,
                fallback_interval,
                ..
            } => {
                assert_eq!(debounce_ms, 500);
                assert_eq!(fallback_interval, 1800);
            }
            _ => panic!("Expected Commands::Ui"),
        }
    }
}
