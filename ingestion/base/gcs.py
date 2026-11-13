import io
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from google.cloud import storage

# Environment variable names
_ENV_START = "INGESTION_START_DATE"
_ENV_END = "INGESTION_END_DATE"
_ENV_BUCKET = "BUCKET_NAME"
_ENV_OUTPUT_DIR = "OUTPUT_DIR"


def _add_pull_date_csv(data: str, pull_date: str) -> str:
    """Add pull_date column to CSV data.

    Args:
        data: CSV content as string.
        pull_date: ISO date string (e.g., "2026-11-10").

    Returns:
        CSV with pull_date column added.
    """
    df = pd.read_csv(io.StringIO(data))
    df["pull_date"] = pull_date
    return df.to_csv(index=False)


def _add_pull_date_jsonl(data: str, pull_date: str) -> str:
    """Add pull_date key to each JSONL record.

    Args:
        data: JSONL content as string (one JSON object per line).
        pull_date: ISO date string (e.g., "2026-11-10").

    Returns:
        JSONL with pull_date key added to each record.
    """
    import json

    lines = []
    for line in data.strip().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        record["pull_date"] = pull_date
        lines.append(json.dumps(record))
    return "\n".join(lines) + "\n"


def _inject_pull_date(data: str, filename: str, pull_date: str) -> str:
    """Inject pull_date into data based on file extension.

    Args:
        data: The data content to process.
        filename: Base filename (used to determine format).
        pull_date: ISO date string for the pull_date column/key.

    Returns:
        Data with pull_date injected.
    """
    _, ext = filename.rsplit(".", 1)
    ext_lower = ext.lower()
    if ext_lower == "csv":
        return _add_pull_date_csv(data, pull_date)
    if ext_lower == "jsonl":
        return _add_pull_date_jsonl(data, pull_date)
    # Unknown format — return data unchanged
    return data


def _generate_blob_name(source: str, filename: str, prefix: str = "compiler-data-lake") -> str:
    """Generate the timestamped file path for a given filename.

    Returns the same path format for both GCS blobs and local files:
    <prefix>/<source>/<YYYY>/<MM>/<DD>/<filename>_<timestamp>.<ext>

    Args:
        source: Source name (e.g., "toggl").
        filename: Base filename (e.g., "timesheets.csv").
        prefix: GCS prefix / local directory prefix.

    Returns:
        Full path string (works for both GCS and local filesystem).
    """
    now = datetime.now(UTC)
    date_path = now.strftime("%Y/%m/%d")
    timestamp = now.strftime("%Y%m%dT%H%M%S")
    name, ext = filename.rsplit(".", 1)
    return f"{prefix}/{source}/{date_path}/{name}_{timestamp}.{ext}"


def _write_to_local(output_dir: str, blob_name: str, data: str) -> str:
    """Write data to local filesystem.

    Args:
        output_dir: Root output directory.
        blob_name: The full path (same format as GCS blob name).
        data: The data content to write.

    Returns:
        The local file path written to.
    """
    file_path = Path(output_dir) / blob_name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        f.write(data)
    return str(file_path)


def _upload_to_gcs(bucket_name: str, blob_name: str, data: str) -> str:
    """Upload pre-processed data to GCS.

    Args:
        bucket_name: Name of the GCS bucket.
        blob_name: The GCS blob path.
        data: The data content to upload (already has pull_date injected).

    Returns:
        The full GCS path of the uploaded file.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type="text/plain")

    return blob_name


def _resolve_bucket(bucket_name: str | None) -> str | None:
    """Resolve the effective bucket name.

    Priority: explicit param > BUCKET_NAME env var > None (local mode).

    Args:
        bucket_name: Explicit bucket name (if provided).

    Returns:
        Bucket name string, or None for local mode.
    """
    if bucket_name:
        return bucket_name
    return os.environ.get(_ENV_BUCKET) or None


def upload_to_storage(
    data: str,
    source: str,
    filename: str,
    prefix: str = "compiler-data-lake",
    pull_date: str | None = None,
    bucket_name: str | None = None,
) -> str:
    """Upload data to storage, falling back to local filesystem.

    Routing is determined by the effective bucket name:
    - If BUCKET_NAME env var is set (or bucket_name param overrides it) → GCS
    - If no bucket name is set → local filesystem (OUTPUT_DIR controls path)

    File path pattern (same for both GCS and local):
    <prefix>/<source>/<YYYY>/<MM>/<DD>/<filename>_<timestamp>.<ext>

    For CSV files, a `pull_date` column is injected.
    For JSONL files, a `pull_date` key is added to each record.

    Args:
        data: The data content to upload (string).
        source: Source name (e.g., "toggl").
        filename: Base filename (e.g., "timesheets.csv").
        prefix: GCS prefix / local directory prefix (default: "compiler-data-lake").
        pull_date: ISO date string for the pull_date column/key.
            Defaults to today's date.
        bucket_name: Optional explicit bucket name (overrides BUCKET_NAME env var).

    Returns:
        The full path of the uploaded file (GCS path or local file path).
    """
    output_dir = os.environ.get(_ENV_OUTPUT_DIR)
    bucket = _resolve_bucket(bucket_name)

    now = datetime.now(UTC)
    if pull_date is None:
        pull_date = now.strftime("%Y-%m-%d")

    blob_name = _generate_blob_name(source, filename, prefix)
    data = _inject_pull_date(data, filename, pull_date)

    if bucket is not None:
        return _upload_to_gcs(bucket, blob_name, data)

    if output_dir is None:
        output_dir = "/tmp/warehouse-ingestion"

    return _write_to_local(output_dir, blob_name, data)
