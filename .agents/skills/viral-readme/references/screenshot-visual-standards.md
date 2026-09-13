# Reference: Screenshot & Visual Media Standards for Open Source

## 1. The Core Law of Visuals
**Developers don't read text until they see the product working.**  
A project without screenshots looks abandoned, theoretical, or CLI-only. A project with crisp, authentic visuals instantly signals high engineering polish and production readiness.

---

## 2. Screenshot Hierarchy in README

### A. The Above-The-Fold Hero Screenshot
- **Placement**: Directly beneath the project badges and 1-sentence value hook.
- **Content**: The primary application interface (e.g. Web UI Dashboard or Main App View) showing real, realistic data—not empty states.
- **Sizing**: `width="92%"` or `width="95%"`, centered with `<p align="center">`.
- **Target Resolution**: 1920x1080 (16:9) or 1440x900 (16:10), retina crisp (device scale factor 2x if possible).

```markdown
<p align="center">
  <img src="docs/assets/screenshots/hero_dashboard.png" alt="Dashboard Preview" width="92%">
</p>
```

---

### B. Feature-Specific In-Action Visuals
Include focused mini-screenshots or side-by-side comparisons alongside specific feature bullet points:
1. **Interactive Diff Comparison**:
   - Split view or slider showing duplicate/look-alike files being compared with similarity metrics.
2. **Terminal Execution Visual**:
   - Clean, syntax-highlighted terminal capture showing CLI scanning, progress bars, and space reclamation.
3. **Settings / Plugins Panel**:
   - Clean table or modal showing plugin registry, toggles, or configurations.

---

## 3. Dark Mode & Light Mode Responsive Picture Syntax

GitHub Flavored Markdown natively supports responsive images that automatically adapt when the viewer switches between GitHub Light and Dark modes:

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/screenshots/dashboard_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/screenshots/dashboard_light.png">
    <img alt="Project Dashboard" src="docs/assets/screenshots/dashboard_dark.png" width="92%">
  </picture>
</p>
```

---

## 4. Asset Organization & Linking Rules

1. **Storage Location**:
   Always store assets in the repository:
   ```
   docs/
     assets/
       screenshots/
         hero_dashboard.png
         visual_diff.png
         cli_execution.png
   ```
2. **Strict Relative Paths**:
   - Use `docs/assets/screenshots/hero_dashboard.png` (relative to root).
   - **NEVER** use external image hosts (Imgur, Cloudinary) — links will expire or get blocked by corporate firewalls.
   - **NEVER** use hardcoded raw GitHub URLs (`https://raw.githubusercontent.com/.../main/...`) — they break on forks, offline environments, and development branches.

---

## 5. Tooling to Capture & Generate Screenshots

| Tool | Purpose | How to Run |
|---|---|---|
| **Playwright** | Programmatic headless browser screenshots of Web UI | `python -m playwright` script against `http://localhost:port` |
| **Rich CLI / SVG** | Beautiful terminal CLI captures | `rich [script] --export-svg cli.svg` |
| **Asciinema / Agg** | Animated terminal GIF captures | `asciinema rec demo.cast && agg demo.cast demo.gif` |
| **Pillow (PIL)** | Programmatic composition, badges, framing | Python Pillow image processing |
