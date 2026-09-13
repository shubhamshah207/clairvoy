"""
Clairvoy Built-in Deduplication Plugins Suite.
"""

from clairvoy.plugins.archive_inspector import ArchiveInspectorMatcherPlugin
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin
from clairvoy.plugins.photo_vision import PhotoVisionMatcherPlugin
from clairvoy.plugins.video_matcher import VideoKeyframeMatcherPlugin

__all__ = [
    "ArchiveInspectorMatcherPlugin",
    "ExactHashMatcherPlugin",
    "PhotoVisionMatcherPlugin",
    "VideoKeyframeMatcherPlugin",
]
