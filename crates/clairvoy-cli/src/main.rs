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
    /// Scan one or more directories for duplicate files
    Scan {
        #[arg(required = true)]
        paths: Vec<PathBuf>,
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
        Commands::Scan { paths } => {
            println!("[*] Initializing Clairvoy Pure Rust Engine across {} path(s)...", paths.len());
            let mut pipeline = clairvoy_engine::DeduplicationPipeline::new(paths);
            pipeline.register_matcher(Arc::new(clairvoy_plugins::ExactHashMatcherPlugin::new()));
            let summary = pipeline.run(|stage, cur, tot| {
                println!(" [>] {}: {} / {}", stage, cur, tot);
            })?;
            println!("\n[✓] Scan complete in {:.2}s. Discovered {} duplicate groups ({:.3} GB recoverable).",
                summary.duration_seconds, summary.total_duplicate_groups, summary.wasted_gb);
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
            clairvoy_server::routes::auto_load_recent_run(&scan_state);

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

            println!("[*] Starting Clairvoy Rust Web Server at http://{} ...", addr);
            let app = clairvoy_server::build_router_with_services(scan_state, db, watcher);
            let listener = tokio::net::TcpListener::bind(addr).await?;
            axum::serve(listener, app).await?;
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
            Commands::Scan { paths } => {
                assert_eq!(paths.len(), 2);
                assert_eq!(paths[0], PathBuf::from("/tmp/dir1"));
                assert_eq!(paths[1], PathBuf::from("/tmp/dir2"));
            }
            _ => panic!("Expected Commands::Scan"),
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
