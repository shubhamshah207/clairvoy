# Reference: Open-Source Diagramming Tools & Ecosystem

## 1. Top Open-Source Diagramming Engines

| Tool | Ecosystem | Strengths | Output Formats |
|---|---|---|---|
| **Mermaid.js** | JavaScript / Native GitHub | Native rendering in GitHub Markdown without compiling, supports zoom/pan, dark mode | Client-side SVG |
| **Diagrams** (`mingrammer/diagrams`) | Python | Define system architectures directly in Python scripts with cloud & tech logos | PNG, SVG, PDF |
| **D2** (Terrastruct) | Go / CLI | Modern declarative language with auto-layout, animations, and dark themes | SVG, PNG, PDF |
| **PlantUML** | Java / Python | Battle-tested UML, sequence, and component diagrams | SVG, PNG |
| **Kroki** | Web Service / Docker | Unified API supporting Mermaid, PlantUML, D2, GraphViz, Excalidraw | SVG, PNG |

---

## 2. Choosing the Right Tool for Open-Source Repositories

1. **For GitHub READMEs**:
   - **Primary Choice**: Pre-rendered, dark-mode **Vector SVG** (`docs/assets/diagrams/architecture.svg`) embedded via `<img src="...">` + **GitHub-Native Mermaid** block.
   - **Why**: Zero external API dependencies, 100% reliable rendering across mobile and desktop, animated pulse flows, and perfect visual consistency with modern Web UIs.

2. **For Complex System Architecture Documentation**:
   - Python `diagrams` or `D2` for multi-service enterprise infrastructure.
