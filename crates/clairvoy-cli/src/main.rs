use clap::{Parser, Subcommand};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

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
        Commands::Ui { host, port } => {
            let addr: SocketAddr = format!("{}:{}", host, port).parse()?;
            println!("[*] Starting Clairvoy Rust Web Server at http://{} ...", addr);
            let app = clairvoy_server::build_router();
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
            Commands::Ui { port, host } => {
                assert_eq!(port, 8000);
                assert_eq!(host, "0.0.0.0");
            }
            _ => panic!("Expected Commands::Ui"),
        }
    }

    #[test]
    fn test_cli_parse_ui_custom_args() {
        let args = vec!["clairvoy-rs", "ui", "--port", "9090", "--host", "127.0.0.1"];
        let cli = Cli::try_parse_from(args).expect("Should parse custom ui arguments");
        match cli.command {
            Commands::Ui { port, host } => {
                assert_eq!(port, 9090);
                assert_eq!(host, "127.0.0.1");
            }
            _ => panic!("Expected Commands::Ui"),
        }
    }
}
