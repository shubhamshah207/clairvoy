# Reference: GitHub-Native Mermaid.js Diagramming

## 1. Overview
GitHub Markdown natively renders Mermaid.js blocks (```mermaid ... ```) directly into interactive, theme-responsive vector SVGs.

---

## 2. Supported Diagram Types on GitHub
- **Flowcharts / Graphs**: `flowchart TD`, `flowchart LR`, `graph TD`
- **Sequence Diagrams**: `sequenceDiagram`
- **Class Diagrams**: `classDiagram`
- **State Diagrams**: `stateDiagram-v2`
- **Entity Relationship**: `erDiagram`

---

## 3. Styling & Dark-Mode Compatibility

### Class Definition (`classDef`)
```mermaid
graph TD
    classDef primary fill:#1e293b,stroke:#6366f1,stroke-width:2px,color:#f8fafc,rx:8px;
    classDef accent fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#f8fafc,rx:8px;

    A[Storage Ingestion]:::primary --> B[Exact Hash Matcher]:::primary
    B --> C[Zero-Space Hardlinks]:::accent
```

### Clickable Interactive Nodes
Mermaid on GitHub supports interactive hyperlinks:
```mermaid
graph LR
    ExactHash["ExactHashMatcherPlugin"]
    click ExactHash "https://github.com/shubhamshah207/clairvoy/blob/main/clairvoy/plugins/exact_hash.py" "View Source"
```

---

## 4. Subgraphs & Pipeline Modeling
Use subgraphs to visually encapsulate pipeline tiers and feedback loops:
```mermaid
graph TD
    subgraph STAGE_1 ["Stage 1: Fast Filtering"]
        Hash["SHA-256"]
    end
    subgraph STAGE_2 ["Stage 2: Deep Vision"]
        Vision["DINOv2 ONNX"]
    end
    Hash -- "Prune Exact" --> Vision
```
