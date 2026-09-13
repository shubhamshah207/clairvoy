"""
Unit tests for Clairvoy Pluggable Engine core interfaces and dynamic PluginRegistry.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import (
    ActionResult,
    BaseActionPlugin,
    BaseKeeperPlugin,
    BaseMatcherPlugin,
    BasePlugin,
    DuplicateCluster,
    PluginRegistry,
)


class DummyMatcher(BaseMatcherPlugin):
    plugin_id = "dummy_matcher"
    display_name = "Dummy Matcher"
    match_type = MatchType.EXACT_HASH
    priority_order = 50

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
        return []


class HighPriorityMatcher(BaseMatcherPlugin):
    plugin_id = "high_priority_matcher"
    display_name = "High Priority Matcher"
    match_type = MatchType.EXACT_HASH
    priority_order = 10

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
        return []


class LowPriorityMatcher(BaseMatcherPlugin):
    plugin_id = "low_priority_matcher"
    display_name = "Low Priority Matcher"
    match_type = MatchType.VISUAL_AI_NEAR_DUPLICATE
    priority_order = 200

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
        return []


class UnavailableMatcher(BaseMatcherPlugin):
    plugin_id = "unavailable_matcher"
    display_name = "Unavailable Matcher"
    match_type = MatchType.VISUAL_AI_NEAR_DUPLICATE
    priority_order = 30

    def is_available(self) -> tuple[bool, str]:
        return False, "Missing dependency: torch and onnxruntime"

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        return []

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict,
    ) -> list[DuplicateCluster]:
        return []


class DummyKeeper(BaseKeeperPlugin):
    plugin_id = "dummy_keeper"
    display_name = "Dummy Keeper"

    def is_available(self) -> tuple[bool, str]:
        return True, "Ready"

    def score_entry(self, entry: FileEntry, cluster: list[FileEntry]) -> int:
        return 100


class DummyAction(BaseActionPlugin):
    plugin_id = "dummy_action"
    display_name = "Dummy Action"
    action_id = "test_quarantine"

    def is_available(self) -> tuple[bool, str]:
        return True, "Ready"

    def execute(self, plan: list, base_dirs: list[Path], dry_run: bool = False) -> ActionResult:
        return ActionResult(
            action_id=self.action_id,
            success_count=len(plan),
            failed_count=0,
            bytes_processed=1024,
            manifest_path="/tmp/manifest.json",
        )


class LifecycleTrackingPlugin(BasePlugin):
    plugin_id = "lifecycle_plugin"
    display_name = "Lifecycle Plugin"

    def __init__(self) -> None:
        super().__init__()
        self.initialized = False
        self.shutdown_called = False
        self.init_context = None

    def is_available(self) -> tuple[bool, str]:
        return True, "Ready"

    def initialize(self, context: dict) -> None:
        self.initialized = True
        self.init_context = context

    def shutdown(self) -> None:
        self.shutdown_called = True


def test_duplicate_cluster_model():
    cluster = DuplicateCluster(
        cluster_id=1,
        match_type=MatchType.EXACT_HASH,
        members=[
            FileEntry(path="/path/a.txt", size_bytes=100),
            FileEntry(path="/path/b.txt", size_bytes=100),
        ],
        similarity_scores=[1.0, 1.0],
        metadata={"hash": "abcdef123456"},
    )
    assert cluster.cluster_id == 1
    assert len(cluster.members) == 2
    assert cluster.similarity_scores == [1.0, 1.0]
    assert cluster.metadata["hash"] == "abcdef123456"

    # Default values check
    cluster_default = DuplicateCluster(
        cluster_id=2,
        match_type=MatchType.VISUAL_AI_NEAR_DUPLICATE,
        members=[],
    )
    assert cluster_default.similarity_scores == []
    assert cluster_default.metadata == {}


def test_action_result_model():
    res = ActionResult(
        action_id="quarantine",
        success_count=5,
        failed_count=1,
        bytes_processed=50000,
        manifest_path="/var/manifest.json",
        errors=["File locked: /path/c.txt"],
    )
    assert res.action_id == "quarantine"
    assert res.success_count == 5
    assert res.failed_count == 1
    assert res.bytes_processed == 50000
    assert res.manifest_path == "/var/manifest.json"
    assert len(res.errors) == 1

    # Validation check
    with pytest.raises(ValidationError):
        ActionResult(
            action_id="invalid",
            success_count="not_an_int",  # type: ignore[arg-type]
            failed_count=0,
            bytes_processed=0,
        )


def test_plugin_registry_registration():
    registry = PluginRegistry()
    matcher = DummyMatcher()
    registry.register(matcher)

    assert "dummy_matcher" in registry.list_plugin_ids()
    assert len(registry) == 1
    assert registry.get_plugin("dummy_matcher") is matcher

    matchers = registry.get_matchers()
    assert len(matchers) == 1
    assert matchers[0].plugin_id == "dummy_matcher"


def test_plugin_registry_type_validation():
    registry = PluginRegistry()
    with pytest.raises(TypeError):
        registry.register("not_a_plugin")  # type: ignore[arg-type]

    class UnidentifiedPlugin(BasePlugin):
        plugin_id = ""
        display_name = "Invalid"

        def is_available(self) -> tuple[bool, str]:
            return True, "Ready"

    with pytest.raises(ValueError):
        registry.register(UnidentifiedPlugin())


def test_plugin_priority_ordering():
    registry = PluginRegistry()
    m_low = LowPriorityMatcher()
    m_high = HighPriorityMatcher()
    m_med = DummyMatcher()

    # Register out of order
    registry.register(m_low)
    registry.register(m_high)
    registry.register(m_med)

    matchers = registry.get_matchers()
    assert len(matchers) == 3
    # Check sorted ascending by priority_order: 10, 50, 200
    assert matchers[0].plugin_id == "high_priority_matcher"
    assert matchers[1].plugin_id == "dummy_matcher"
    assert matchers[2].plugin_id == "low_priority_matcher"


def test_plugin_enable_disable():
    registry = PluginRegistry()
    matcher = DummyMatcher()
    registry.register(matcher)

    assert registry.is_plugin_enabled("dummy_matcher") is True
    assert len(registry.get_matchers(enabled_only=True)) == 1

    # Disable plugin
    assert registry.disable_plugin("dummy_matcher") is True
    assert registry.is_plugin_enabled("dummy_matcher") is False
    assert len(registry.get_matchers(enabled_only=True)) == 0
    assert len(registry.get_matchers(enabled_only=False)) == 1

    # Re-enable plugin
    assert registry.enable_plugin("dummy_matcher") is True
    assert registry.is_plugin_enabled("dummy_matcher") is True
    assert len(registry.get_matchers(enabled_only=True)) == 1

    # Non-existent plugin operations
    assert registry.enable_plugin("non_existent") is False
    assert registry.disable_plugin("non_existent") is False


def test_plugin_categories_and_lookups():
    registry = PluginRegistry()
    matcher = DummyMatcher()
    keeper = DummyKeeper()
    action = DummyAction()

    registry.register(matcher)
    registry.register(keeper)
    registry.register(action)

    assert len(registry.get_matchers()) == 1
    assert len(registry.get_keepers()) == 1
    assert len(registry.get_actions()) == 1

    # Lookup action by action_id and by plugin_id
    assert registry.get_action("test_quarantine") is action
    assert registry.get_action("dummy_action") is action
    assert registry.get_action("non_existent") is None


def test_plugin_lifecycle_and_unregistration():
    registry = PluginRegistry()
    plugin = LifecycleTrackingPlugin()
    registry.register(plugin)

    plugin.initialize({"scan_id": "123"})
    assert plugin.initialized is True
    assert plugin.init_context == {"scan_id": "123"}
    assert plugin.shutdown_called is False

    # Unregister triggers shutdown
    registry.unregister("lifecycle_plugin")
    assert plugin.shutdown_called is True
    assert "lifecycle_plugin" not in registry.list_plugin_ids()
    assert registry.get_plugin("lifecycle_plugin") is None


def test_graceful_degradation_unavailable_plugin():
    registry = PluginRegistry()
    matcher = UnavailableMatcher()
    registry.register(matcher)

    plugin = registry.get_plugin("unavailable_matcher")
    assert plugin is not None
    is_avail, reason = plugin.is_available()
    assert is_avail is False
    assert "Missing dependency" in reason

    # Matchers query with available_only=True filters it out
    assert len(registry.get_matchers(available_only=False)) == 1
    assert len(registry.get_matchers(available_only=True)) == 0


def test_dynamic_plugin_loader_from_dir(temp_workspace):
    plugin_dir = temp_workspace / "plugins"
    plugin_dir.mkdir()
    plugin_file = plugin_dir / "custom_keeper.py"
    plugin_file.write_text(
        """
from clairvoy.core.plugins import BaseKeeperPlugin

class CustomKeeper(BaseKeeperPlugin):
    plugin_id = "custom_keeper"
    display_name = "Custom Keeper"

    def is_available(self):
        return True, "Ready"

    def score_entry(self, entry, cluster):
        return 999
"""
    )

    # Add a file that should be ignored (__init__.py)
    (plugin_dir / "__init__.py").write_text("# init")

    # Add a non-python file that should be ignored
    (plugin_dir / "readme.txt").write_text("plugin documentation")

    registry = PluginRegistry()
    loaded = registry.load_plugins_from_directory(plugin_dir)
    assert len(loaded) == 1
    assert loaded[0].plugin_id == "custom_keeper"
    assert "custom_keeper" in registry.list_plugin_ids()

    keepers = registry.get_keepers()
    assert len(keepers) == 1
    assert keepers[0].score_entry(None, []) == 999  # type: ignore[arg-type]


def test_dynamic_plugin_loader_nonexistent_dir(temp_workspace):
    registry = PluginRegistry()
    loaded = registry.load_plugins_from_directory(temp_workspace / "non_existent")
    assert loaded == []


def test_dynamic_plugin_loader_malformed_syntax(temp_workspace):
    plugin_dir = temp_workspace / "bad_plugins"
    plugin_dir.mkdir()
    (plugin_dir / "broken.py").write_text("def broken_syntax( {")

    registry = PluginRegistry()
    loaded = registry.load_plugins_from_directory(plugin_dir)
    assert loaded == []


def test_load_entry_points():
    registry = PluginRegistry()

    mock_ep = MagicMock()
    mock_ep.name = "ep_matcher"
    mock_ep.load.return_value = DummyMatcher

    with patch("importlib.metadata.entry_points") as mock_entry_points:
        mock_entry_points.return_value = [mock_ep]
        loaded = registry.load_entry_points(group="clairvoy.plugins")
        assert len(loaded) == 1
        assert loaded[0].plugin_id == "dummy_matcher"
        assert "dummy_matcher" in registry.list_plugin_ids()


def test_thread_safe_concurrent_registration():
    registry = PluginRegistry()

    def register_worker(worker_id: int):
        class WorkerPlugin(BasePlugin):
            plugin_id = f"worker_{worker_id}"
            display_name = f"Worker {worker_id}"

            def is_available(self) -> tuple[bool, str]:
                return True, "Ready"

        registry.register(WorkerPlugin())

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(register_worker, range(50)))

    assert len(registry.list_plugin_ids()) == 50
