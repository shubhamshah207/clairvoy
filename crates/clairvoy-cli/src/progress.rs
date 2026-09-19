use std::io::{self, Write};
use std::time::Instant;

pub struct TerminalProgressBar {
    title: String,
    total: usize,
    current: usize,
    bar_width: usize,
    start_time: Instant,
    last_rendered: Instant,
    is_finished: bool,
}

impl TerminalProgressBar {
    pub fn new(title: &str, total: usize) -> Self {
        Self {
            title: title.to_string(),
            total,
            current: 0,
            bar_width: 28,
            start_time: Instant::now(),
            last_rendered: Instant::now(),
            is_finished: false,
        }
    }

    pub fn set_title(&mut self, title: &str) {
        self.title = title.to_string();
    }

    pub fn set_total(&mut self, total: usize) {
        self.total = total;
    }

    pub fn update(&mut self, current: usize, message: &str) {
        self.current = current;
        let now = Instant::now();
        // Throttle updates to at most once every 50ms unless it's the end
        if now.duration_since(self.last_rendered).as_millis() < 40 && current < self.total && self.total > 0 {
            return;
        }
        self.last_rendered = now;
        self.render(message);
    }

    pub fn render(&self, message: &str) {
        if self.is_finished {
            return;
        }

        let elapsed = self.start_time.elapsed().as_secs_f64().max(0.001);
        let rate = (self.current as f64) / elapsed;
        let rate_str = if rate >= 1000.0 {
            format!("{:.1}k/s", rate / 1000.0)
        } else {
            format!("{:.0}/s", rate)
        };

        let elapsed_mins = (elapsed as u64) / 60;
        let elapsed_secs = (elapsed as u64) % 60;
        let time_str = format!("{:02}:{:02}", elapsed_mins, elapsed_secs);

        let mut stdout = io::stdout();
        if self.total > 0 {
            let pct = ((self.current as f64 / self.total as f64) * 100.0).min(100.0);
            let filled_len = ((pct / 100.0) * (self.bar_width as f64)).round() as usize;
            let empty_len = self.bar_width.saturating_sub(filled_len);

            let bar: String = "█".repeat(filled_len) + &"░".repeat(empty_len);

            let eta_str = if pct > 0.0 && pct < 100.0 && rate > 0.0 {
                let remaining = (self.total - self.current) as f64 / rate;
                let eta_mins = (remaining as u64) / 60;
                let eta_secs = (remaining as u64) % 60;
                format!(" ETA {:02}:{:02}", eta_mins, eta_secs)
            } else {
                String::new()
            };

            let _ = write!(
                stdout,
                "\r\x1B[2K\x1B[36m[{}]\x1B[0m \x1B[1m{:>5.1}%\x1B[0m | \x1B[33m{}/{}\x1B[0m | \x1B[32m{}\x1B[0m [{}{}]",
                bar,
                pct,
                format_number(self.current),
                format_number(self.total),
                truncate_str(message, 36),
                time_str,
                eta_str
            );
        } else {
            // Indeterminate bar animation
            let spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
            let spin_idx = ((elapsed * 10.0) as usize) % spinner.len();

            let _ = write!(
                stdout,
                "\r\x1B[2K\x1B[36m{}\x1B[0m | \x1B[33m{} items\x1B[0m | \x1B[32m{}\x1B[0m ({} | {})",
                spinner[spin_idx],
                format_number(self.current),
                truncate_str(message, 40),
                rate_str,
                time_str
            );
        }
        let _ = stdout.flush();
    }

    pub fn finish(&mut self, message: &str) {
        if self.is_finished {
            return;
        }
        self.is_finished = true;
        let elapsed = self.start_time.elapsed().as_secs_f64();
        let mut stdout = io::stdout();
        let _ = writeln!(
            stdout,
            "\r\x1B[2K\x1B[32m[✓]\x1B[0m {} \x1B[90m({:.2}s)\x1B[0m",
            message, elapsed
        );
        let _ = stdout.flush();
    }

    pub fn fail(&mut self, message: &str) {
        self.is_finished = true;
        let mut stdout = io::stdout();
        let _ = writeln!(stdout, "\r\x1B[2K\x1B[31m[✗]\x1B[0m Error: {}", message);
        let _ = stdout.flush();
    }
}

fn format_number(n: usize) -> String {
    let s = n.to_string();
    let mut result = String::new();
    for (count, c) in s.chars().rev().enumerate() {
        if count > 0 && count % 3 == 0 {
            result.push(',');
        }
        result.push(c);
    }
    result.chars().rev().collect()
}

fn truncate_str(s: &str, max_len: usize) -> String {
    if s.chars().count() <= max_len {
        s.to_string()
    } else {
        let truncated: String = s.chars().take(max_len.saturating_sub(3)).collect();
        format!("{}...", truncated)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_number() {
        assert_eq!(format_number(0), "0");
        assert_eq!(format_number(999), "999");
        assert_eq!(format_number(1000), "1,000");
        assert_eq!(format_number(43086), "43,086");
        assert_eq!(format_number(1000000), "1,000,000");
    }

    #[test]
    fn test_truncate_str() {
        assert_eq!(truncate_str("hello", 10), "hello");
        assert_eq!(truncate_str("superlongstringthatexceeds", 10), "superlo...");
    }

    #[test]
    fn test_terminal_progress_bar_lifecycle() {
        let mut pb = TerminalProgressBar::new("Test task", 100);
        assert_eq!(pb.total, 100);
        assert_eq!(pb.current, 0);
        assert!(!pb.is_finished);

        pb.update(50, "Halfway done");
        assert_eq!(pb.current, 50);

        pb.finish("Task completed");
        assert!(pb.is_finished);
    }

    #[test]
    fn test_terminal_progress_bar_indeterminate() {
        let mut pb = TerminalProgressBar::new("Crawling", 0);
        assert_eq!(pb.total, 0);

        pb.update(250, "Discovered files");
        assert_eq!(pb.current, 250);

        pb.set_total(1000);
        assert_eq!(pb.total, 1000);

        pb.fail("Something went wrong");
        assert!(pb.is_finished);
    }
}
