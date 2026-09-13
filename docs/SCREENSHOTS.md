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

## ⚡ Generating & Updating Screenshots

### Automated Generation via Script
Run the automated screenshot script from the repository root:

```bash
python scripts/capture_screenshots.py
```

This script will:
1. Render a clean vector SVG of the terminal execution (`cli_execution.svg`) using `rich`.
2. Verify existing high-resolution Web UI screenshots or attempt automated headless browser capture via Playwright.

---

## 🌐 Capturing Web UI Screenshots Manually

If you update the Web UI and want to capture new screenshots from your local desktop browser:

```bash
# 1. Launch the Web UI server
clairvoy ui --port 8000

# 2. Open http://localhost:8000 in your browser (Chrome, Safari, or Edge)
# 3. Enter a scan path, run a deduplication scan, and open the visual diff modal
# 4. Snap the screen at 1920x1080 or 1440x900 resolution
# 5. Save the images to:
#    - docs/assets/screenshots/dashboard_preview.png
#    - docs/assets/screenshots/visual_diff.png
```

---

## 🧪 Automated Integrity Testing

Documentation integrity is enforced by unit tests:

```bash
pytest tests/test_docs_integrity.py -v
```

This test guarantees that:
- Every image referenced in `README.md` exists on disk and is non-empty.
- All relative markdown links resolve to valid files.
- `README.md` does not exceed GitHub's 500 KiB truncation limit.
