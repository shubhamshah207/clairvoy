# Clairvoy Screenshot & Documentation Assets Guide

This guide outlines how screenshots and visual assets are organized, generated, and verified in the Clairvoy project.

---

## 📁 Screenshot Storage & Structure

All screenshots referenced in [`README.md`](../README.md) and project documentation are stored strictly within the repository:

```
docs/
  assets/
    screenshots/
      dashboard_preview.png   # Hero Web UI Dashboard capture
      visual_diff.png         # Side-by-side photo comparison modal
      cli_execution.svg       # Vector SVG terminal CLI capture
```

### Invariants & Rules
1. **Always Use Relative Paths**: Never link to external hosting services (Imgur, Cloudinary) or hardcoded branch URLs (`raw.githubusercontent.com/...`).
2. **Above-the-Fold Hero Image**: Keep `dashboard_preview.png` centered immediately beneath the project badges in `README.md`.
3. **Keep Total README Size Under 500 KiB**: GitHub truncates rendered markdown files exceeding 500 KiB. Compressed PNGs and vector SVGs keep repository download sizes minimal.

---

## 🌐 Capturing Web UI Screenshots Manually

To capture new screenshots from your local desktop browser:

```bash
# 1. Launch the pure Rust Web UI server
cargo run --bin clairvoy-rs -- ui --port 8000

# 2. Open http://localhost:8000 in your browser (Chrome, Safari, or Edge)
# 3. Enter a scan path, run a deduplication scan, and open the visual diff modal
# 4. Snap the screen at 1920x1080 or 1440x900 resolution
# 5. Save the images to:
#    - docs/assets/screenshots/dashboard_preview.png
#    - docs/assets/screenshots/visual_diff.png
```

---

## 🧪 Workspace Verification

All repository tests and verification are executed via Cargo:

```bash
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```

