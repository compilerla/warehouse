"""Tests for Toggl subprocess data fetching and puller integration."""

from io import StringIO
from subprocess import CompletedProcess
from unittest.mock import patch

import pandas as pd
import pytest

from ingestion.toggl.pull import _CLI, TogglPuller, _fetch_clients, _fetch_project_users, _fetch_projects, _fetch_timesheets, _fetch_users


def _make_mock_result(stdout: str) -> CompletedProcess[str]:
    """Create a mock CompletedProcess with the given stdout."""
    return CompletedProcess(args=[_CLI, "fake"], returncode=0, stdout=stdout, stderr="")


def _make_mock_error(stderr: str) -> CompletedProcess[str]:
    """Create a mock CompletedProcess representing a failed CLI call."""
    return CompletedProcess(args=["compiler-admin", "fake"], returncode=1, stdout="", stderr=stderr)


def _make_timesheet_csv() -> str:
    return (
        "id,user_id,project_id,description,start_time,end_time,duration,billable,created_at,updated_at,workspace_id\n"
        "1,10,100,Work,2026-11-10 09:00:00,2026-11-10 17:00:00,28800,1,2026-11-10 09:00:00,2026-11-10 17:00:00,123456\n"
    )


def _make_users_csv() -> str:
    return (
        "email,name,id,user_id,role_id,organization_id,inactive,joined,can_edit_email,2fa_enabled,avatar_url\n"
        "alice@example.com,Alice,10,1001,1,10,0,2024-01-15,1,1,\n"
        "bob@example.com,Bob,20,1002,2,10,0,2024-03-20,1,0,\n"
    )


def _make_clients_csv() -> str:
    return (
        "id,name,created_at,updated_at,workspace_id\n"
        "5,Acme Corp,2024-01-01 00:00:00,2024-06-01 00:00:00,123456\n"
    )


def _make_projects_csv() -> str:
    return (
        "id,name,description,client_id,active,billable,private,currency,rate,estimated_seconds,actual_seconds,created_at,updated_at,workspace_id\n"
        "100,Project Alpha,Alpha project,5,1,1,0,USD,150.0,360000,180000,2024-03-01 00:00:00,2024-08-01 00:00:00,123456\n"
    )


def _make_project_users_csv() -> str:
    return (
        "id,user_id,project_id,workspace_id,rate,labor_cost\n"
        "1,10,100,123456,150.0,100.0\n"
        "2,20,100,123456,120.0,80.0\n"
    )


class TestFetchTimesheets:
    """Tests for _fetch_timesheets."""

    def test_fetch_timesheets_stdout_csv(self):
        """Test that timesheets are fetched via compiler-admin time download --stdout."""
        csv_data = (
            "id,user_id,project_id,description,start_time,end_time,duration,billable,created_at,updated_at,workspace_id\n"
            "1,10,100,Work,2026-11-10 09:00:00,2026-11-10 17:00:00,28800,1,2026-11-10 09:00:00,2026-11-10 17:00:00,123456\n"
        )

        with patch("ingestion.toggl.pull.subprocess.run") as mock_run:
            mock_run.return_value = _make_mock_result(csv_data)
            result = _fetch_timesheets("2026-11-10", "2026-11-10")

        mock_run.assert_called_once_with(
            [_CLI, "time", "download", "--stdout", "--start", "2026-11-10", "--end", "2026-11-10"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result["id"].iloc[0] == 1
        assert result["billable"].iloc[0] == 1
        assert result["workspace_id"].iloc[0] == 123456


class TestFetchUsers:
    """Tests for _fetch_users."""

    def test_fetch_users_csv(self):
        """Test that users are fetched via compiler-admin ls users toggl --format csv."""
        csv_data = (
            "email,name,id,user_id,role_id,organization_id,inactive,joined,can_edit_email,2fa_enabled,avatar_url\n"
            "alice@example.com,Alice,10,1001,1,10,0,2024-01-15,1,1,\n"
            "bob@example.com,Bob,20,1002,2,10,0,2024-03-20,1,0,\n"
        )

        with patch("ingestion.toggl.pull.subprocess.run") as mock_run:
            mock_run.return_value = _make_mock_result(csv_data)
            result = _fetch_users()

        mock_run.assert_called_once_with(
            [_CLI, "ls", "users", "toggl", "--format", "csv"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert result["name"].iloc[0] == "Alice"
        assert result["2fa_enabled"].iloc[1] == 0


class TestFetchClients:
    """Tests for _fetch_clients."""

    def test_fetch_clients_csv(self):
        """Test that clients are fetched via compiler-admin ls clients --format csv."""
        csv_data = (
            "id,name,created_at,updated_at,workspace_id\n"
            "5,Acme Corp,2024-01-01 00:00:00,2024-06-01 00:00:00,123456\n"
        )

        with patch("ingestion.toggl.pull.subprocess.run") as mock_run:
            mock_run.return_value = _make_mock_result(csv_data)
            result = _fetch_clients()

        mock_run.assert_called_once_with(
            [_CLI, "ls", "clients", "--format", "csv"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result["name"].iloc[0] == "Acme Corp"


class TestFetchProjects:
    """Tests for _fetch_projects."""

    def test_fetch_projects_csv(self):
        """Test that projects are fetched via compiler-admin ls projects --format csv."""
        csv_data = (
            "id,name,description,client_id,active,billable,private,currency,rate,estimated_seconds,actual_seconds,created_at,updated_at,workspace_id\n"
            "100,Project Alpha,Alpha project,5,1,1,0,USD,150.0,360000,180000,2024-03-01 00:00:00,2024-08-01 00:00:00,123456\n"
        )

        with patch("ingestion.toggl.pull.subprocess.run") as mock_run:
            mock_run.return_value = _make_mock_result(csv_data)
            result = _fetch_projects()

        mock_run.assert_called_once_with(
            [_CLI, "ls", "projects", "--format", "csv"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result["name"].iloc[0] == "Project Alpha"
        assert result["currency"].iloc[0] == "USD"
        assert result["rate"].iloc[0] == 150.0


class TestFetchProjectUsers:
    """Tests for _fetch_project_users."""

    def test_fetch_project_users_csv(self):
        """Test that project users are fetched via compiler-admin ls project-users --format csv."""
        csv_data = (
            "id,user_id,project_id,workspace_id,rate,labor_cost\n"
            "1,10,100,123456,150.0,100.0\n"
            "2,20,100,123456,120.0,80.0\n"
        )

        with patch("ingestion.toggl.pull.subprocess.run") as mock_run:
            mock_run.return_value = _make_mock_result(csv_data)
            result = _fetch_project_users()

        mock_run.assert_called_once_with(
            [_CLI, "ls", "project-users", "--format", "csv"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert result["user_id"].iloc[0] == 10
        assert result["rate"].iloc[0] == 150.0


class TestTogglPuller:
    """Tests for the TogglPuller CLI integration."""

    def _make_subprocess_side_effect(self):
        """Return a side-effect function for subprocess.run that returns CSV for each call."""
        csvs = [
            _make_timesheet_csv(),
            _make_users_csv(),
            _make_clients_csv(),
            _make_projects_csv(),
            _make_project_users_csv(),
        ]
        call_count = [0]

        def side_effect(*args, **kwargs):
            result = _make_mock_result(csvs[call_count[0]])
            call_count[0] += 1
            return result

        return side_effect

    def test_pull_calls_all_five_fetchers(self):
        """Test that pull invokes all five CLI data fetchers."""
        with patch("ingestion.toggl.pull.subprocess.run") as mock_run:
            mock_run.side_effect = self._make_subprocess_side_effect()
            with patch("ingestion.toggl.pull.upload_to_storage") as mock_upload:
                mock_upload.return_value = "compiler-data-lake/toggl/2026/11/10/timesheets_20261110T000000.csv"

                puller = TogglPuller()
                paths = puller.pull("toggl", "2026-11-10", "2026-11-10")

                assert len(paths) == 5
                assert mock_run.call_count == 5

    def test_pull_returns_five_paths(self):
        """Test that pull returns one path per data type (5 data types)."""
        side_effect = self._make_subprocess_side_effect()

        with patch("ingestion.toggl.pull.subprocess.run", side_effect=side_effect):
            with patch("ingestion.toggl.pull.upload_to_storage") as mock_upload:
                mock_upload.return_value = "compiler-data-lake/toggl/2026/11/10/timesheets_20261110T000000.csv"

                puller = TogglPuller()
                paths = puller.pull("toggl", "2026-11-10", "2026-11-10")

                assert len(paths) == 5

    def test_pull_injects_pull_date(self):
        """Test that pull_date is passed to upload_to_storage."""
        side_effect = self._make_subprocess_side_effect()

        with patch("ingestion.toggl.pull.subprocess.run", side_effect=side_effect):
            with patch("ingestion.toggl.pull.upload_to_storage") as mock_upload:
                mock_upload.return_value = "compiler-data-lake/toggl/2026/11/10/timesheets_20261110T000000.csv"

                puller = TogglPuller()
                puller.pull("toggl", "2026-11-10", "2026-11-10")

                assert mock_upload.call_count == 5
                for call in mock_upload.call_args_list:
                    kwargs = call[1]
                    assert kwargs.get("pull_date") == "2026-11-10"

    def test_pull_uses_correct_filenames(self):
        """Test that pull uses the correct filenames for each data type."""
        side_effect = self._make_subprocess_side_effect()

        with patch("ingestion.toggl.pull.subprocess.run", side_effect=side_effect):
            with patch("ingestion.toggl.pull.upload_to_storage") as mock_upload:
                mock_upload.return_value = "compiler-data-lake/toggl/2026/11/10/timesheets_20261110T000000.csv"

                puller = TogglPuller()
                puller.pull("toggl", "2026-11-10", "2026-11-10")

                filenames = [call[0][2] for call in mock_upload.call_args_list]
                assert "timesheets.csv" in filenames
                assert "users.csv" in filenames
                assert "clients.csv" in filenames
                assert "projects.csv" in filenames
                assert "project_users.csv" in filenames

    def test_pull_cli_called_with_correct_args(self):
        """Test that subprocess.run is called with the correct compiler-admin arguments."""
        responses = [
            _make_mock_result(_make_timesheet_csv()),
            _make_mock_result(_make_users_csv()),
            _make_mock_result(_make_clients_csv()),
            _make_mock_result(_make_projects_csv()),
            _make_mock_result(_make_project_users_csv()),
        ]
        call_order = [0]

        def side_effect(*args, **kwargs):
            result = responses[call_order[0]]
            call_order[0] += 1
            return result

        with patch("ingestion.toggl.pull.subprocess.run", side_effect=side_effect) as mock_run:
            with patch("ingestion.toggl.pull.upload_to_storage"):
                puller = TogglPuller()
                puller.pull("toggl", "2026-11-10", "2026-11-10")

        expected_calls = [
            ["compiler-admin", "time", "download", "--stdout", "--start", "2026-11-10", "--end", "2026-11-10"],
            ["compiler-admin", "ls", "users", "toggl", "--format", "csv"],
            ["compiler-admin", "ls", "clients", "--format", "csv"],
            ["compiler-admin", "ls", "projects", "--format", "csv"],
            ["compiler-admin", "ls", "project-users", "--format", "csv"],
        ]

        assert mock_run.call_count == 5
        for i, call_args in enumerate(mock_run.call_args_list):
            assert call_args[0][0] == expected_calls[i]

    def test_pull_cli_error_raises(self):
        """Test that a CLI error raises RuntimeError."""
        with patch("ingestion.toggl.pull.subprocess.run") as mock_run:
            mock_run.return_value = _make_mock_error("API error: Forbidden")

            puller = TogglPuller()
            with pytest.raises(RuntimeError, match="timesheets failed"):
                puller.pull("toggl", "2026-11-10", "2026-11-10")
