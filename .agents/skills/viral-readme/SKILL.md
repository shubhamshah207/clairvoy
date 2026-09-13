---
name: viral-readme
description: Use when creating or refining a repository README.md, project documentation, or visual assets to maximize open-source presentation, clarity, and developer adoption.
---

# Viral Open-Source README & Documentation Architecture

## Overview

A great README is the primary sales page and user onboarding flow for an open-source project. Developers decide whether to star, fork, or use a tool within **5 seconds** of landing on GitHub.

This skill defines the battle-tested engineering standard for creating high-converting, visually striking, and community-ready open-source documentation.

### Core References
- [GitHub Official Specification](references/github-official-spec.md) (Discovery precedence, 500 KiB limit, relative linking)
- [Screenshot & Visual Standards](references/screenshot-visual-standards.md) (Hero placement, aspect ratios, dark/light mode syntax)
- [Viral Growth & Community Checklist](references/viral-growth-checklist.md) (5-second test, comparison matrix, community docs)

---

## 1. Golden Rules of High-Impact Documentation

1. **Visuals Above the Fold**:
   - Every user-facing tool **MUST** have a hero screenshot or animated recording directly beneath the title and badges.
   - Show the product working with realistic data before explaining architecture or history.

2. **Branch-Resilient Relative Links**:
   - Always use repository-relative paths (`docs/assets/screenshots/...`).
   - Never use raw CDN URLs (`raw.githubusercontent.com/...`) or external hosting services that break on forks or offline environments.
   - Link text must remain on a single line to prevent GitHub Markdown rendering errors.

3. **Strict Size Budget**:
   - GitHub truncates READMEs exceeding 500 KiB. Keep the main README focused on quickstart and features; place extended manuals in `docs/`.

4. **The 30-Second Quickstart**:
   - Provide a copy-pasteable installation command and a 1-line execution example within the top two scroll lengths.

---

## 2. Standard Viral README Information Hierarchy

```
+----------------------------------------------------------------------------------------------------+
|                               VIRAL README LAYOUT & INFORMATION HIERARCHY                          |
+----------------------------------------------------------------------------------------------------+
|  [1] HERO HEADER                                                                                   |
|      • Project Name + Catchy Tagline ("Clear, fast, local-first storage deduplication")            |
|      • Dynamic Badges (CI Status, PyPI, License, Python Versions, GitHub Stars)                    |
+----------------------------------------------------------------------------------------------------+
|  [2] VISUAL PROOF (Above the Fold)                                                                 |
|      • High-resolution Screenshot or Animated Demo GIF of the Web UI / CLI in action                |
+----------------------------------------------------------------------------------------------------+
|  [3] THE 30-SECOND QUICKSTART                                                                      |
|      • `pip install <project>`                                                                     |
|      • 1-liner run command                                                                         |
+----------------------------------------------------------------------------------------------------+
|  [4] "WHY THIS PROJECT?" (Comparison Matrix)                                                       |
|      • Feature Comparison Table vs. Top Alternatives                                               |
+----------------------------------------------------------------------------------------------------+
|  [5] FEATURE SHOWCASE WITH EMBEDDED SCREENSHOTS                                                    |
|      • Screenshot 1: Interactive Web UI / Dashboard                                                |
|      • Screenshot 2: Side-by-Side Comparison / Diff                                                |
|      • Screenshot 3: Terminal CLI Execution                                                        |
+----------------------------------------------------------------------------------------------------+
|  [6] ARCHITECTURE & DESIGN PATTERNS (ASCII Text Diagram)                                           |
|      • Priority-ordered pipeline, component relationships, data flow                               |
+----------------------------------------------------------------------------------------------------+
|  [7] ACCOMPANYING COMMUNITY FILES                                                                  |
|      • CONTRIBUTING.md, LICENSE, SECURITY.md, CITATION.cff, .github/ISSUE_TEMPLATE/                |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Screenshot Formatting & Syntax

### A. Centered Hero Screenshot
```html
<p align="center">
  <img src="docs/assets/screenshots/hero_dashboard.png" alt="Dashboard Preview" width="92%">
</p>
```

### B. Adaptive Dark/Light Mode Screenshot
When the application supports dark and light themes:
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

## 4. Accompanying Open-Source Files Suite

Every high-standard open-source repository must pair its README with:
- `LICENSE`: OSI-approved license (Apache 2.0 or MIT).
- `CONTRIBUTING.md`: Clean setup steps, test execution commands, plugin authoring guidelines.
- `SECURITY.md`: Vulnerability reporting process and security boundaries.
- `CITATION.cff`: Citation metadata for research attribution.
- `.github/ISSUE_TEMPLATE/`: Form-based issue templates for bugs and features.
