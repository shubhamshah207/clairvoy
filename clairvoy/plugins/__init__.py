"""
Clairvoy Built-in Deduplication Plugins Suite.
"""

from clairvoy.plugins.archive_inspector import ArchiveInspectorMatcherPlugin
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin

__all__ = [
    "ArchiveInspectorMatcherPlugin",
    "ExactHashMatcherPlugin",
]
