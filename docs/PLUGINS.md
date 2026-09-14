# Clairvoy Plugin Developer Guide

Clairvoy is designed from the ground up as a pluggable, extensible deduplication platform. This guide covers how to develop, test, and register custom plugins.

---

## 1. Plugin Types & Contracts

All plugins derive from [`BasePlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py):

```
                       +-------------------+
                       |    BasePlugin     |
                       +---------+---------+
                                 |
         +-----------------------+-----------------------+
         |                       |                       |
         v                       v                       v
+-------------------+   +-------------------+   +-------------------+
| BaseMatcherPlugin |   | BaseKeeperPlugin  |   | BaseActionPlugin  |
+-------------------+   +-------------------+   +-------------------+
```

### Matcher Plugin (`BaseMatcherPlugin`)
Implements candidate grouping and duplicate clustering.
- `plugin_id: str` (unique identifier)
- `display_name: str`
- `priority_order: int` (Determines execution order; lower runs first)
  - `10-19`: Exact byte/hash matchers
  - `20-29`: Visual / neural embedding matchers
  - `30-39`: Audio / video temporal matchers
  - `40-49`: Container / archive inspectors
- `filter_supported(candidates: list[FileEntry]) -> list[FileEntry]`
- `find_duplicates(candidates, all_indexed_files, context) -> list[DuplicateCluster]`

### Keeper Strategy Plugin (`BaseKeeperPlugin`)
Scores files within a duplicate cluster to select which one to preserve.
- `score_entry(entry: FileEntry, cluster: DuplicateCluster) -> float`

### Action Plugin (`BaseActionPlugin`)
Executes resolution against duplicate records.
- `execute(records: list[DuplicateRecord], base_dirs: list[Path]) -> ActionResult`

---

## 2. Creating a Custom Matcher

Here is a minimal example of a custom filename-stem matcher plugin:

```python
# ~/.clairvoy/plugins/stem_matcher.py
from pathlib import Path
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import BaseMatcherPlugin, DuplicateCluster


class StemMatcherPlugin(BaseMatcherPlugin):
    plugin_id = "stem_matcher"
    display_name = "Filename Stem Matcher"
    match_type = MatchType.SIMILAR_VISUAL
    priority_order = 45

    def is_available(self) -> tuple[bool, str]:
        return True, "Ready"

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        return files

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict,
    ) -> list[DuplicateCluster]:
        from collections import defaultdict
        grouped = defaultdict(list)
        for f in candidates:
            stem = Path(f.path).stem.lower().strip()
            grouped[stem].append(f)

        clusters = []
        for stem, members in grouped.items():
            if len(members) > 1:
                clusters.append(
                    DuplicateCluster(
                        match_type=self.match_type,
                        members=members,
                        confidence=0.85,
                        plugin_id=self.plugin_id,
                        metadata={"stem": stem},
                    )
                )
        return clusters
```

---

## 3. Dynamic Discovery & Loading

Clairvoy discovers and loads plugins from three distinct sources:

1. **Built-in Bundled Plugins**: Loaded automatically from `clairvoy.plugins`.
2. **User Plugin Directory**: Python files placed in `~/.clairvoy/plugins/` (or passed via `--plugin-dir`) are discovered dynamically via `importlib`.
3. **Setuptools Entry Points**: Third-party packages registered under the entry point group `clairvoy.plugins`:
   ```toml
   [project.entry-points."clairvoy.plugins"]
   custom_matcher = "my_package.plugins:MyCustomMatcher"
   ```

---

## 4. CLI Inspection & Toggling

```bash
# List all discovered plugins, versions, priority, and enabled status
clairvoy plugins list

# Inspect detailed metadata for a plugin
clairvoy plugins info exact_hash

# Run scan with specific plugins enabled or disabled
clairvoy scan /media/photos --enable-plugin custom_matcher --disable-plugin archive_inspector
```
