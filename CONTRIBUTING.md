# Contributing to Clairvoy

Thank you for your interest in contributing to Clairvoy! We welcome contributions of all kinds, including new deduplication matcher plugins, keeper ranking strategies, UI improvements, and documentation polish.

---

## 🛠️ Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/shubhamshah207/clairvoy.git
cd clairvoy

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install in editable mode with development, ML, and documentation dependencies
pip install -e ".[dev,ml,docs]"
```

---

## 🧪 Running Tests & Quality Checks

Clairvoy maintains a strict 100% test pass rate with zero linter errors:

```bash
# Run the entire test suite
pytest -v

# Run the linter
ruff check .

# Format code
ruff format .
```

---

## 📸 Updating Documentation & Screenshots

Clairvoy adheres to the **viral-readme** documentation standard. All screenshots must be stored in `docs/assets/screenshots/` and referenced using relative paths.

To regenerate or verify documentation assets:

```bash
# Run the automated screenshot pipeline
python scripts/capture_screenshots.py

# Verify documentation integrity
pytest tests/test_docs_integrity.py
```

---

## 🔌 Writing Custom Plugins

Clairvoy features a dynamic GoF plugin architecture. Custom plugins can be dropped directly into `~/.clairvoy/plugins/` without modifying core code.

### Example Custom Matcher Plugin (`~/.clairvoy/plugins/custom_matcher.py`)

```python
from typing import Any
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import BaseMatcherPlugin, DuplicateCluster


class CustomAudioMatcherPlugin(BaseMatcherPlugin):
    plugin_id: str = "custom_audio_matcher"
    display_name: str = "Custom Audio Fingerprint Matcher"
    version: str = "0.1.0"
    author: str = "Community Contributor"
    description: str = "Matches audio files using acoustic fingerprinting"
    match_type: MatchType = MatchType.EXACT_HASH
    priority_order: int = 35

    def is_available(self) -> tuple[bool, str]:
        return True, "Available via standard library"

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        return [f for f in files if f.path.lower().endswith((".mp3", ".flac", ".wav"))]

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict[str, Any] | None = None,
    ) -> list[DuplicateCluster]:
        # Implement duplicate discovery logic
        return []
```

Verify your plugin is loaded:
```bash
clairvoy plugins list
```

---

## 📬 Pull Request Guidelines

1. Ensure all tests pass: `pytest && ruff check .`
2. If introducing user-facing features, update [`README.md`](README.md) and include/update relevant screenshots.
3. Commit messages should follow [Conventional Commits](https://www.conventionalcommits.org/) format (e.g. `feat(plugins): ...`, `fix(cli): ...`, `docs: ...`).
