---
name: diagrams-as-code
description: Use when designing, generating, or embedding rich, dynamic, or animated architecture diagrams and flowcharts for project documentation and GitHub READMEs.
---

# Diagrams as Code & Rich Visual Architecture Skill

## Overview

High-quality open-source projects replace plain text and raw ASCII with **rich, visually polished, or dynamic architecture diagrams** that immediately convey system structure, data flow, and design patterns.

This skill defines standards and tooling for creating rich, animated vector SVGs and GitHub-native Mermaid diagrams at the project level.

### Core References
- [GitHub-Native Mermaid Syntax](references/mermaid-github-syntax.md) (Class styling, subgraphs, clickable nodes)
- [Vector SVG Standards](references/vector-svg-standards.md) (CSS pulse animations, dark slate palette, Retina scaling)
- [Diagrams Tools Ecosystem](references/diagrams-tools-ecosystem.md) (Mermaid, D2, Python Diagrams, Kroki)

---

## 1. The Two-Tier Diagramming Standard for GitHub

To maximize visual impact while retaining native maintainability, use a **two-tier architecture presentation**:

1. **Tier 1: High-Impact Animated Vector SVG (Primary Visual)**:
   - Generated via project-level Python script: `scripts/generate_architecture_diagram.py`.
   - Stored in repository: `docs/assets/diagrams/architecture.svg`.
   - Features: Glassmorphism cards, glowing status borders, linear gradients, and CSS `@keyframes` animated pulse connectors.
   - Embedded directly in `README.md`:
     ```html
     <p align="center">
       <img src="docs/assets/diagrams/architecture.svg" alt="Clairvoy Pluggable Architecture" width="98%">
     </p>
     ```

2. **Tier 2: Interactive GitHub-Native Mermaid (Collapsible / Interactive)**:
   - Placed in a `<details><summary>` toggle or documentation section.
   - Allows visitors to inspect diagram source, copy nodes, or edit flowcharts directly in GitHub.

---

## 2. Project-Level Generator Script Pattern

Every project using rich diagrams should maintain an automated generator in `scripts/`:

```bash
# Run the diagram generator script
python scripts/generate_architecture_diagram.py
```

### Generator Script Responsibilities
- Construct scalable vector elements with `viewBox`.
- Define responsive CSS animations for connector lines (`stroke-dasharray`, `pulseFlow`).
- Emit `.svg` into `docs/assets/diagrams/`.
- Ensure zero external web font dependencies to satisfy GitHub camo proxy requirements.

---

## 3. GitHub Mermaid Invariants

When writing native Mermaid blocks in Markdown:
- Always use `graph TD` or `flowchart TD` for pipeline/vertical flows.
- Use `classDef` to match the project's color palette (e.g. dark slate `#1e293b`, emerald `#10b981`, indigo `#6366f1`).
- Enclose multiline labels in quotes with `<br/>` tags.
- Avoid unsupported diagram types (use flowcharts for roadmaps and pipelines).
