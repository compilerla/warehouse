"""Toggl puller — fetches timesheets, users, clients, projects, and project users.

Uses subprocess calls to the compiler-admin CLI binary. compiler-admin must be
installed on PATH (it is available in the dev container and CI environments).
"""

import subprocess
from io import StringIO

import pandas as pd

from ingestion.base.gcs import upload_to_storage
from ingestion.base.pull import Puller

TIMESHEET_FILENAME = "timesheets.csv"
PROJECTS_FILENAME = "projects.csv"
USERS_FILENAME = "users.csv"
CLIENTS_FILENAME = "clients.csv"
PROJECT_USERS_FILENAME = "project_users.csv"

_CLI = "compiler-admin"


def _run_cli(args: list[str], label: str) -> str:
    """Run a compiler-admin CLI command and return stdout.

    Logs to stderr for visibility. Raises ``RuntimeError`` if the process
    returns a non-zero exit code.

    Args:
        args: Arguments to pass to compiler-admin (after the base command).
        label: Human-readable label for logging.

    Returns:
        Stdout content from the CLI command.

    Raises:
        RuntimeError: If the CLI command fails.
    """
    cmd = [_CLI, *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.stderr:
        print(f"[{label}] stderr: {result.stderr.strip()}", flush=True)
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout


def _fetch_timesheets(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch timesheet data via ``compiler-admin time download --stdout``.

    Args:
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    Returns:
        DataFrame with raw timesheet CSV data.
    """
    raw = _run_cli(
        [
            "time",
            "download",
            "--stdout",
            "--start",
            start_date,
            "--end",
            end_date,
        ],
        "timesheets",
    )
    return pd.read_csv(StringIO(raw))


def _fetch_users() -> pd.DataFrame:
    """Fetch user data via ``compiler-admin ls users toggl --format csv``.

    Returns:
        DataFrame with raw user CSV data.
    """
    raw = _run_cli(["ls", "users", "toggl", "--format", "csv"], "users")
    return pd.read_csv(StringIO(raw))


def _fetch_projects() -> pd.DataFrame:
    """Fetch project data via ``compiler-admin ls projects --format csv``.

    Returns:
        DataFrame with raw project CSV data.
    """
    raw = _run_cli(["ls", "projects", "--format", "csv"], "projects")
    return pd.read_csv(StringIO(raw))


def _fetch_clients() -> pd.DataFrame:
    """Fetch client data via ``compiler-admin ls clients --format csv``.

    Returns:
        DataFrame with raw client CSV data.
    """
    raw = _run_cli(["ls", "clients", "--format", "csv"], "clients")
    return pd.read_csv(StringIO(raw))


def _fetch_project_users() -> pd.DataFrame:
    """Fetch project-user assignment data via ``compiler-admin ls project-users --format csv``.

    Returns:
        DataFrame with raw project-user CSV data.
    """
    raw = _run_cli(["ls", "project-users", "--format", "csv"], "project-users")
    return pd.read_csv(StringIO(raw))


class TogglPuller(Puller):
    """Puller for Toggl data (timesheets, users, clients, projects, project users).

    Fetches data by invoking the `compiler-admin` CLI binary and uploads
    CSV files to GCS (or local filesystem if `OUTPUT_DIR` is set).
    """

    source_name = "toggl"

    def pull(
        self,
        source: str,
        start_date: str | None = None,
        end_date: str | None = None,
        bucket_name: str | None = None,
    ) -> list[str]:
        """Pull all Toggl data for the given date range.

        Args:
            source: Source name (used for path prefix).
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            bucket_name: GCS bucket name (overrides BUCKET_NAME env var).

        Returns:
            List of uploaded file paths.
        """
        paths = []

        # 1. Timesheets
        timesheet_df = _fetch_timesheets(start_date, end_date)
        csv_data = timesheet_df.to_csv(index=False)
        path = upload_to_storage(csv_data, source, TIMESHEET_FILENAME, pull_date=start_date, bucket_name=bucket_name)
        paths.append(path)

        # 2. Users
        users_df = _fetch_users()
        csv_data = users_df.to_csv(index=False)
        path = upload_to_storage(csv_data, source, USERS_FILENAME, pull_date=start_date, bucket_name=bucket_name)
        paths.append(path)

        # 3. Clients
        clients_df = _fetch_clients()
        csv_data = clients_df.to_csv(index=False)
        path = upload_to_storage(csv_data, source, CLIENTS_FILENAME, pull_date=start_date, bucket_name=bucket_name)
        paths.append(path)

        # 4. Projects
        projects_df = _fetch_projects()
        csv_data = projects_df.to_csv(index=False)
        path = upload_to_storage(csv_data, source, PROJECTS_FILENAME, pull_date=start_date, bucket_name=bucket_name)
        paths.append(path)

        # 5. Project users
        project_users_df = _fetch_project_users()
        csv_data = project_users_df.to_csv(index=False)
        path = upload_to_storage(csv_data, source, PROJECT_USERS_FILENAME, pull_date=start_date, bucket_name=bucket_name)
        paths.append(path)

        return paths
