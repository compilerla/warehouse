"""Tests for Puller discovery and module scanning."""

import types
from unittest.mock import patch

from ingestion.base.pull import Puller, _collect_pullers, discover_pullers


def _make_fake_module(*classes) -> types.ModuleType:
    """Create a fake module containing the given classes."""
    mod = types.ModuleType("fake_source")
    for cls in classes:
        setattr(mod, cls.__name__, cls)
    return mod


class _FakeSourceA(Puller):
    """A fake puller for testing."""

    source_name = "fake_a"

    def pull(self, source: str, start_date: str | None = None, end_date: str | None = None) -> list[str]:
        return []


class _FakeSourceB(Puller):
    """Another fake puller for testing."""

    source_name = "fake_b"

    def pull(self, source: str, start_date: str | None = None, end_date: str | None = None) -> list[str]:
        return []


class _NonPuller:
    """Not a Puller — should be ignored."""


class TestCollectPullers:
    """Tests for _collect_pullers."""

    def test_discovers_pullers_with_source_name(self):
        """Test that Puller subclasses with source_name are collected."""
        fake_mod = _make_fake_module(_FakeSourceA, _FakeSourceB)
        results = _collect_pullers(fake_mod)
        assert results == {"fake_a": _FakeSourceA, "fake_b": _FakeSourceB}

    def test_ignores_non_puller_classes(self):
        """Test that non-Puller classes are skipped."""
        fake_mod = _make_fake_module(_FakeSourceA, _NonPuller)
        results = _collect_pullers(fake_mod)
        assert "nonpuller" not in results
        assert results["fake_a"] is _FakeSourceA

    def test_ignores_base_puller_class(self):
        """Test that the base Puller class is not collected (no source_name)."""
        fake_mod = _make_fake_module(Puller)
        results = _collect_pullers(fake_mod)
        assert not results

    def test_ignores_puller_without_source_name(self):
        """Test that Puller subclasses without source_name are skipped."""

        class _OrphanPuller(Puller):
            """A puller with no source_name."""

            def pull(self, source: str, start_date: str | None = None, end_date: str | None = None) -> list[str]:
                return []

        fake_mod = _make_fake_module(_OrphanPuller)
        results = _collect_pullers(fake_mod)
        assert not results

    def test_returns_new_dict_each_call(self):
        """Test that each call returns an independent dict."""
        fake_mod = _make_fake_module(_FakeSourceA)
        r1 = _collect_pullers(fake_mod)
        r2 = _collect_pullers(fake_mod)
        assert r1 == r2
        assert r1 is not r2


class TestDiscoverPullers:
    """Tests for discover_pullers."""

    def test_discovers_real_pullers(self):
        """Test that discover_pullers finds pullers in the ingestion package."""
        results = discover_pullers()
        # TogglPuller is registered in the ingestion package
        assert "toggl" in results
        assert results["toggl"].__name__ == "TogglPuller"

    def test_accepts_custom_base_package(self):
        """Test that a custom base_package argument works with injected modules."""
        fake_mod = _make_fake_module(_FakeSourceA)

        fake_pkg = types.ModuleType("test_discover_pkg")
        fake_pkg.__path__ = ["/dev/null"]

        fake_walk_result = [
            (None, "test_discover_pkg.fake_source", False),
        ]

        with (
            patch("ingestion.base.pull.pkgutil.walk_packages", return_value=fake_walk_result),
            patch(
                "ingestion.base.pull.importlib.import_module",
                side_effect=lambda name, *a, **k: fake_mod if name == "test_discover_pkg.fake_source" else fake_pkg,
            ),
        ):
            results = discover_pullers(base_package="test_discover_pkg")
            assert "fake_a" in results
            assert results["fake_a"] is _FakeSourceA

    def test_import_error_triggers_continue_path(self):
        """Test that ImportError triggers the continue path in discover_pullers."""
        import importlib as _importlib

        original_import = _importlib.import_module

        def _import_side_effect(name, *args, **kwargs):
            if name == "good_module":
                return _make_fake_module(_FakeSourceA)
            if name == "bad_module":
                raise ImportError(f"cannot import {name}")
            # Let real imports pass through for pkgutil, etc.
            return original_import(name, *args, **kwargs)

        fake_walk_result = [
            (None, "good_module", False),
            (None, "bad_module", False),
        ]

        with (
            patch("ingestion.base.pull.importlib.import_module", side_effect=_import_side_effect),
            patch("ingestion.base.pull.pkgutil.walk_packages", return_value=fake_walk_result),
        ):
            results = discover_pullers()
            assert "fake_a" in results
            assert results["fake_a"] is _FakeSourceA

    def test_handles_import_errors_in_modules(self):
        """Test that modules that fail to import are skipped."""
        # The real ingestion package has optional dependencies — this tests
        # that ImportError from walk_packages doesn't crash discovery.
        results = discover_pullers()
        # Should not raise, should just skip problematic modules
        assert isinstance(results, dict)
