# Adding a New Ingestion Source

This guide walks through adding a new data source to the ingestion framework. The framework uses a plugin-style architecture: you create a source package, implement a `Puller` subclass, and the framework auto-discovers it at runtime.

## Architecture Overview

The ingestion framework consists of three layers:

1. **Base layer** (`ingestion.base/`) — shared utilities: `Puller` base class, GCS/local upload, secret retrieval, CLI helpers.
2. **Source packages** (`ingestion/<source>/`) — each source is its own Python package with a `pull.py` containing a `Puller` subclass.
3. **Entry point** (`ingestion/main.py`) — discovers all `Puller` subclasses and dispatches CLI commands.

Auto-discovery means **no manual registration is needed** — just add a new module with a `Puller` subclass and it will be picked up automatically.

---

## 1. Create the Source Package

```bash
mkdir -p ingestion/my_source
touch ingestion/my_source/__init__.py
touch ingestion/my_source/pull.py
```

The package structure:

```
ingestion/my_source/
├── __init__.py      # Empty or re-exports (optional)
└── pull.py          # Contains the Puller subclass
```

---

## 2. Implement the Puller

Create `ingestion/my_source/pull.py`:

```python
from ingestion.base.pull import Puller
from ingestion.base.gcs import upload_to_storage


class MySourcePuller(Puller):
    """Pull data from MySource."""

    source_name = "my_source"

    def pull(
        self,
        source: str,
        start_date: str | None = None,
        end_date: str | None = None,
        bucket_name: str | None = None,
    ) -> list[str]:
        """Pull MySource data for the given date range.

        Args:
            source: Source name (used for path prefix).
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            bucket_name: GCS bucket name (overrides BUCKET_NAME env var).

        Returns:
            List of uploaded file paths (GCS or local).
        """
        paths = []

        # Fetch data from the source (return CSV or JSONL string)
        data = fetch_data(start_date, end_date)

        # Upload to GCS (or local filesystem)
        path = upload_to_storage(
            data=data,
            source=source,
            filename="data.csv",
            pull_date=start_date,
        )
        paths.append(path)

        return paths


def fetch_data(start_date: str, end_date: str) -> str:
    """Fetch raw data as a string (CSV or JSONL).

    The framework injects a ``pull_date`` column/key into the output.
    """
    ...
    return csv_data
```

### Key Requirements

| Requirement   | Details                                                                                                   |
| ------------- | --------------------------------------------------------------------------------------------------------- |
| `source_name` | Class attribute identifying the source (used for CLI dispatch and GCS path). Must match the package name. |
| `pull()`      | Must return `list[str]` — one entry per uploaded file. The list is logged but not otherwise consumed.     |
| `data` format | String containing CSV or JSONL. Other formats are passed through unchanged (no `pull_date` injection).    |

### Real-World Example: Toggl

The Toggl source (`ingestion/toggl/pull.py`) is the reference implementation. It:

- Defines `source_name = "toggl"`
- Fetches 5 data types (timesheets, users, clients, projects, project-users)
- Calls `upload_to_storage()` for each data type
- Returns a list of 5 GCS/local paths

Each data type has its own filename constant (e.g., `TIMESHEET_FILENAME = "timesheets.csv"`).

---

## 3. Handle Secrets

If the source requires API tokens or credentials, use the `get_secret` helper from `ingestion.base.secrets`:

```python
from ingestion.base.secrets import get_secret

class MySourcePuller(Puller):
    source_name = "my_source"

    def pull(self, source, start_date=None, end_date=None):
        token = get_secret("my-source-api-token")
        ...
```

The helper currently reads secrets from environment variables. In production, secrets are injected into the Cloud Run Job's environment from Google Secret Manager via the Terraform configuration (see [Create Secrets](#3-create-secrets) above).

### Registering Secrets

Create the secret in Google Cloud:

```bash
gcloud secrets create my-source-api-token \
  --data-plaintext-file=/path/to/token \
  --replication-policy=automatic \
  --project=data-warehouse-492522
```

---

## 4. Add Dependencies (Optional)

If the source requires additional Python packages, add them as an optional dependency in `pyproject.toml`:

```toml
[project.optional-dependencies]
my_source = [
    "my-source-sdk>=1.0",
]
```

Add `my_source` to the setuptools packages list:

```toml
[tool.setuptools]
packages = ["ingestion", "ingestion.base", "ingestion.toggl", "ingestion.my_source"]
```

The optional dependency group (`my_source`) can be installed during the Docker build if needed:

```dockerfile
RUN pip install .[my_source]
```

Add `my_source` to the devcontainer's pip install so you can test locally:

```dockerfile
RUN pip install .[toggl,my_source]
```

Update `.devcontainer/Dockerfile` and any relevant `postCreate.sh` or `setup.sh` scripts accordingly.

---

## 5. Test Locally

Run a test pull without GCP credentials (uses local filesystem mode):

```bash
ingestion my_source pull --start 2026-10-01 --end 2026-10-31
```

Check the output:

```bash
ls -la /tmp/warehouse-ingestion/my_source/
```

The files will be written to `/tmp/warehouse-ingestion/` when no bucket is specified.

### Testing with GCS

To test GCS uploads locally, use `--bucket`:

```bash
ingestion my_source pull --start 2026-10-01 --end 2026-10-31 --bucket compiler-data-lake
```

---

## 6. Add Terraform Infrastructure

Deploy the source to production by adding Terraform resources in `terraform/modules/ingestion/`:

### Cloud Run Job

A Cloud Run Job runs `ingestion my_source pull` with the appropriate date range arguments.

### Cloud Scheduler

A Cloud Scheduler job triggers the Cloud Run Job on a schedule (e.g., daily).

### IAM Bindings

The service account needs:

- `roles/storage.objectCreator` on the data lake bucket
- `roles/secretmanager.secretAccessor` for any source-specific secrets

### Secret Manager

Add source-specific secrets (API tokens, credentials) to Google Secret Manager.

---

## 7. Deploy

Push a release tag (e.g., `2026.11.20`) to trigger the CI/CD workflow. The new source is included in the base image (`ghcr.io/compilerla/warehouse/ingestion/base:<sha>`) since it lives in the `ingestion/` package.

Deploy the Cloud Run Job and Cloud Scheduler separately via Terraform.

---

## Checklist

- [ ] Created `ingestion/<source>/pull.py` with a `Puller` subclass
- [ ] Set `source_name` to match the package name
- [ ] `pull()` returns `list[str]` of uploaded file paths
- [ ] Added dependencies to `pyproject.toml` (if needed)
- [ ] Added `my_source` to `[tool.setuptools].packages`
- [ ] Created secrets in Google Secret Manager (if needed)
- [ ] Added `my_source` to devcontainer pip install
- [ ] Tested locally (`ingestion my_source pull --start ... --end ...`)
- [ ] Added Cloud Run Job, Scheduler, and IAM in Terraform
- [ ] Pushed release tag and verified the deployment

## What's Next

- See the [Adding a New Ingestion Source](../tutorials/ingestion-source.md) tutorial for a complete end-to-end walkthrough with code samples.
- See the [Ingestion Operations Guide](ingestion-operations.md) for monitoring, troubleshooting, and ad-hoc pull procedures.
- See the [Deploying to Production](../explanation/deployment-production.md) guide for a detailed explanation of the CI/CD pipeline.
