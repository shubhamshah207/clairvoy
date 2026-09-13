# Reference: Viral Open Source Growth & Repository Polish Checklist

## 1. The 5-Second Attention Test
Developers landing on GitHub evaluate repositories through a rapid visual scan:

1. **Title + Tagline**: 1 crisp sentence without jargon.
2. **Badges**: Proof of vitality (Python version, License, Build status, PyPI).
3. **Hero Screenshot**: Visual proof that the project is real, functional, and visually appealing.
4. **Copy-Paste Quickstart**: 2 commands max (`pip install ...`, `run ...`).
5. **Comparison Matrix**: Instant differentiation against known alternatives.

---

## 2. The Feature Comparison Matrix
Trending projects (e.g. *uv*, *ruff*, *ripgrep*, *fastapi*) always include a feature matrix highlighting technical advantages:

| Feature | Your Project | Competitor A | Competitor B |
|---|:---:|:---:|:---:|
| **Local-First & Offline** | ✅ | ✅ | ❌ |
| **AI Visual Transformer** | ✅ | ❌ | ❌ |
| **Zero-Space Hardlinks** | ✅ | ❌ | ⚠️ |
| **Pluggable Architecture**| ✅ | ❌ | ❌ |
| **Interactive Web UI** | ✅ | ❌ | ✅ |

---

## 3. Accompanying Open-Source Community Files

To be viewed as enterprise-grade and trustworthy:

1. **`LICENSE`**: Clear open-source license (e.g., Apache 2.0 or MIT).
2. **`CONTRIBUTING.md`**:
   - Environment setup in under 5 commands.
   - Test execution guidelines (`pytest`).
   - Plugin creation instructions.
3. **`SECURITY.md`**:
   - Security boundaries (path traversal, system directory protection).
   - Responsible disclosure policy.
4. **`CITATION.cff`**:
   - Machine-readable academic citation metadata.
5. **`.github/ISSUE_TEMPLATE/`**:
   - `bug_report.yml`
   - `feature_request.yml`
