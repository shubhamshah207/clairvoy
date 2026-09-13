"""
Clairvoy Pluggable Engine Core Interfaces and Dynamic Registry.

Implements Gang-of-Four (GoF) compliant interfaces for:
- Tiered Duplicate Matching (Pipeline / Chain of Responsibility)
- Keeper Retention Scoring (Strategy)
- Duplicate Resolution & Rollback (Strategy)
- Dynamic Discovery & Lifecycle (Registry / Service Locator)
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import inspect
import logging
import sys
import threading
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from clairvoy.core.models import FileEntry, MatchType

logger = logging.getLogger(__name__)


class DuplicateCluster(BaseModel):
    """Logical cluster of duplicate files discovered by a matcher plugin."""

    cluster_id: int
    match_type: MatchType
    members: list[FileEntry]
    similarity_scores: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    """Metrics and manifest details returned by an action plugin execution."""

    action_id: str
    success_count: int
    failed_count: int
    bytes_processed: int
    manifest_path: str | None = None
    errors: list[str] = Field(default_factory=list)


class BasePlugin(ABC):
    """Abstract base class for all Clairvoy plugins."""

    plugin_id: str = ""
    display_name: str = ""
    version: str = "0.1.0"
    author: str = "Clairvoy"
    description: str = ""
    enabled_by_default: bool = True

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability.

        Returns:
            tuple[bool, str]: (is_available, status_or_reason)
        """
        ...

    def initialize(self, context: dict[str, Any]) -> None:  # noqa: B027
        """Optional lifecycle setup hook called prior to pipeline execution."""
        pass

    def shutdown(self) -> None:  # noqa: B027
        """Optional lifecycle cleanup hook called during teardown."""
        pass


class BaseMatcherPlugin(BasePlugin):
    """Abstract matcher plugin in the deduplication pipeline hierarchy."""

    match_type: MatchType = MatchType.EXACT_HASH
    priority_order: int = 100

    @abstractmethod
    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        """Filter files supported by this matcher (e.g., media types, extensions)."""
        ...

    @abstractmethod
    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict[str, Any],
    ) -> list[DuplicateCluster]:
        """Discover clusters of duplicate files."""
        ...


class BaseKeeperPlugin(BasePlugin):
    """Abstract strategy for scoring candidate files in a duplicate cluster."""

    @abstractmethod
    def score_entry(self, entry: FileEntry, cluster: list[FileEntry]) -> int:
        """Score an entry within a cluster. Higher integer score wins as the keeper."""
        ...


class BaseActionPlugin(BasePlugin):
    """Abstract strategy for resolving duplicate files (quarantine, hardlink, etc.)."""

    action_id: str = ""

    @abstractmethod
    def execute(
        self,
        plan: list[Any],
        base_dirs: list[Path],
        dry_run: bool = False,
    ) -> ActionResult:
        """Execute the resolution action on the duplicate plan."""
        ...


class PluginRegistry:
    """Thread-safe dynamic registry managing plugin discovery, lifecycle, and access."""

    _instance: ClassVar[PluginRegistry | None] = None
    _class_lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        """Access or instantiate the process-wide singleton PluginRegistry."""
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the process-wide singleton PluginRegistry instance (for tests)."""
        with cls._class_lock:
            if cls._instance is not None:
                cls._instance.clear()
                cls._instance = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._plugins: dict[str, BasePlugin] = {}
        self._enabled: dict[str, bool] = {}

    def __len__(self) -> int:
        with self._lock:
            return len(self._plugins)

    def register(self, plugin: BasePlugin) -> None:
        """Register a plugin instance with the registry."""
        if not isinstance(plugin, BasePlugin):
            raise TypeError(f"Expected BasePlugin instance, got {type(plugin).__name__}")
        if not plugin.plugin_id or not isinstance(plugin.plugin_id, str):
            raise ValueError("Plugin must have a non-empty string plugin_id")

        with self._lock:
            self._plugins[plugin.plugin_id] = plugin
            if plugin.plugin_id not in self._enabled:
                self._enabled[plugin.plugin_id] = getattr(plugin, "enabled_by_default", True)

    def unregister(self, plugin_id: str) -> None:
        """Unregister a plugin and invoke its shutdown lifecycle hook."""
        with self._lock:
            plugin = self._plugins.pop(plugin_id, None)
            self._enabled.pop(plugin_id, None)

        if plugin is not None:
            try:
                plugin.shutdown()
            except Exception as exc:
                logger.warning("Error during shutdown of plugin %s: %s", plugin_id, exc)

    def get_plugin(self, plugin_id: str) -> BasePlugin | None:
        """Retrieve a registered plugin by plugin_id."""
        with self._lock:
            return self._plugins.get(plugin_id)

    def list_plugin_ids(self) -> list[str]:
        """List all registered plugin identifiers."""
        with self._lock:
            return list(self._plugins.keys())

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a registered plugin."""
        with self._lock:
            if plugin_id in self._plugins:
                self._enabled[plugin_id] = True
                return True
            return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a registered plugin."""
        with self._lock:
            if plugin_id in self._plugins:
                self._enabled[plugin_id] = False
                return True
            return False

    def is_plugin_enabled(self, plugin_id: str) -> bool:
        """Check if a registered plugin is currently enabled."""
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            return self._enabled.get(plugin_id, True)

    def get_matchers(
        self,
        enabled_only: bool = True,
        available_only: bool = False,
    ) -> list[BaseMatcherPlugin]:
        """Retrieve matcher plugins sorted by priority_order ascending."""
        with self._lock:
            matchers = [p for p in self._plugins.values() if isinstance(p, BaseMatcherPlugin)]
            if enabled_only:
                matchers = [p for p in matchers if self._enabled.get(p.plugin_id, True)]
            if available_only:
                matchers = [p for p in matchers if p.is_available()[0]]
            return sorted(matchers, key=lambda p: p.priority_order)

    def get_keepers(
        self,
        enabled_only: bool = True,
        available_only: bool = False,
    ) -> list[BaseKeeperPlugin]:
        """Retrieve keeper strategy plugins."""
        with self._lock:
            keepers = [p for p in self._plugins.values() if isinstance(p, BaseKeeperPlugin)]
            if enabled_only:
                keepers = [p for p in keepers if self._enabled.get(p.plugin_id, True)]
            if available_only:
                keepers = [p for p in keepers if p.is_available()[0]]
            return keepers

    def get_actions(
        self,
        enabled_only: bool = True,
        available_only: bool = False,
    ) -> list[BaseActionPlugin]:
        """Retrieve action resolution plugins."""
        with self._lock:
            actions = [p for p in self._plugins.values() if isinstance(p, BaseActionPlugin)]
            if enabled_only:
                actions = [p for p in actions if self._enabled.get(p.plugin_id, True)]
            if available_only:
                actions = [p for p in actions if p.is_available()[0]]
            return actions

    def get_action(self, action_id: str) -> BaseActionPlugin | None:
        """Retrieve an action plugin matching action_id or plugin_id."""
        with self._lock:
            for plugin in self._plugins.values():
                if isinstance(plugin, BaseActionPlugin) and (
                    getattr(plugin, "action_id", None) == action_id
                    or plugin.plugin_id == action_id
                ):
                    return plugin
            return None

    def clear(self) -> None:
        """Shut down all registered plugins and clear registry state."""
        with self._lock:
            plugins_to_shutdown = list(self._plugins.values())
            self._plugins.clear()
            self._enabled.clear()

        for plugin in plugins_to_shutdown:
            try:
                plugin.shutdown()
            except Exception as exc:
                logger.warning("Error during shutdown of %s: %s", plugin.plugin_id, exc)

    def load_plugins_from_directory(self, dir_path: Path | str) -> list[BasePlugin]:
        """Scan directory for python files, load modules, and register BasePlugin subclasses."""
        path = Path(dir_path).expanduser().resolve()
        if not path.is_dir():
            logger.warning("Plugin directory %s does not exist or is not a directory.", path)
            return []

        loaded: list[BasePlugin] = []
        py_files = sorted(path.glob("*.py"))

        for py_file in py_files:
            if py_file.name.startswith("__"):
                continue

            unique_module_name = f"clairvoy_plugin_{py_file.stem}_{uuid.uuid4().hex[:8]}"
            try:
                spec = importlib.util.spec_from_file_location(unique_module_name, py_file)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[unique_module_name] = module
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, BasePlugin)
                        and obj not in (BasePlugin, BaseMatcherPlugin, BaseKeeperPlugin, BaseActionPlugin)
                        and not inspect.isabstract(obj)
                        and getattr(obj, "__module__", None) == module.__name__
                    ):
                        try:
                            instance = obj()
                            self.register(instance)
                            loaded.append(instance)
                        except Exception as init_err:
                            logger.error(
                                "Failed to instantiate plugin class %s from %s: %s",
                                attr_name,
                                py_file,
                                init_err,
                            )
            except Exception as load_err:
                logger.error("Failed to load plugin module from %s: %s", py_file, load_err)

        return loaded

    def load_entry_points(self, group: str = "clairvoy.plugins") -> list[BasePlugin]:
        """Discover and load plugins registered via package entry points."""
        loaded: list[BasePlugin] = []
        try:
            eps = importlib.metadata.entry_points()
            if hasattr(eps, "select"):
                matched_eps = list(eps.select(group=group))
            elif isinstance(eps, dict):
                matched_eps = list(eps.get(group, []))
            else:
                try:
                    matched_eps = list(importlib.metadata.entry_points(group=group))
                except Exception:
                    matched_eps = []
        except Exception as err:
            logger.warning("Failed to query entry points for group %s: %s", group, err)
            return []

        for ep in matched_eps:
            try:
                target = ep.load()
                if (
                    isinstance(target, type)
                    and issubclass(target, BasePlugin)
                    and not inspect.isabstract(target)
                ):
                    instance = target()
                elif isinstance(target, BasePlugin):
                    instance = target
                else:
                    continue
                self.register(instance)
                loaded.append(instance)
            except Exception as ep_err:
                logger.warning("Failed to load entry point %s: %s", ep.name, ep_err)

        return loaded


__all__ = [
    "ActionResult",
    "BaseActionPlugin",
    "BaseKeeperPlugin",
    "BaseMatcherPlugin",
    "BasePlugin",
    "DuplicateCluster",
    "FileEntry",
    "MatchType",
    "PluginRegistry",
]
