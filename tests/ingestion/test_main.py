"""Tests for CLI registration and module-level auto-discovery."""

from unittest.mock import patch

import click
import pytest

from ingestion.main import main, register_source


def _make_fake_puller(source_name: str = "test") -> type:
    """Create a minimal Puller subclass for testing registration."""
    return type(
        "FakePuller",
        (),
        {
            "source_name": source_name,
            "pull": lambda self, source, start_date=None, end_date=None: [],
        },
    )


class TestRegisterSource:
    """Tests for register_source."""

    def test_adds_command_to_group(self):
        """Test that register_source adds a subcommand to the group."""
        group = click.Group()
        FakePuller = _make_fake_puller()
        register_source(group, "fake", FakePuller)
        assert "fake" in group.commands

    def test_command_is_click_command(self):
        """Test that the registered command is a Click Command."""
        group = click.Group()
        FakePuller = _make_fake_puller()
        register_source(group, "fake", FakePuller)
        fake_cmd = group.commands["fake"]
        assert isinstance(fake_cmd, click.Command)

    def test_command_rejects_invalid_action(self):
        """Test that the command only accepts 'pull' as action."""
        group = click.Group()
        FakePuller = _make_fake_puller()
        register_source(group, "fake", FakePuller)
        fake_cmd = group.commands["fake"]

        with pytest.raises(click.exceptions.BadParameter):
            fake_cmd.main(["invalid"], standalone_mode=False)

    def test_command_passes_source_name_to_puller(self):
        """Test that pull() receives the correct source name."""
        group = click.Group()
        FakePuller = _make_fake_puller()
        register_source(group, "fake", FakePuller)
        fake_cmd = group.commands["fake"]

        with patch.object(FakePuller, "pull") as mock_pull:
            fake_cmd.main(["pull", "--start", "2026-01-01", "--end", "2026-01-31"], standalone_mode=False)
            mock_pull.assert_called_once()
            call_kwargs = mock_pull.call_args[1]
            assert call_kwargs["source"] == "fake"
            assert call_kwargs["start_date"] == "2026-01-01"
            assert call_kwargs["end_date"] == "2026-01-31"


class TestMainCLI:
    """Tests for the main CLI group."""

    def test_main_is_click_group(self):
        """Test that main is a Click group."""
        assert isinstance(main, click.Group)

    def test_toggl_command_registered(self):
        """Test that toggl is registered via auto-discovery."""
        assert "toggl" in main.commands

    def test_toggl_command_is_click_command(self):
        """Test that registered sources are Click Commands."""
        toggl_cmd = main.commands["toggl"]
        assert isinstance(toggl_cmd, click.Command)

    def test_pull_command_has_date_options(self):
        """Test that the toggl command has --start and --end options."""
        toggl_cmd = main.commands["toggl"]
        param_names = {p.name for p in toggl_cmd.params}
        assert "start_date" in param_names
        assert "end_date" in param_names
