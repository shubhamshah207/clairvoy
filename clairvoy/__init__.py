"""
Clairvoy: Local-first AI storage deduplication engine with CLI & Web UI.
"""

import os

# Cap glibc memory arenas to prevent multi-threaded virtual memory fragmentation
os.environ.setdefault("MALLOC_ARENA_MAX", "2")

__version__ = "0.1.0"
__author__ = "Shubham Shah"

