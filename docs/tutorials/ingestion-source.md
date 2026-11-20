# Adding a New Ingestion Source

This tutorial walks through the complete end-to-end process of adding a new ingestion source. We will build a contrived `acme_api` source that fetches CSV data from a mock API endpoint and uploads it to storage.

> **Prerequisites**: Follow the [Getting Started](../tutorials/getting-started.md) tutorial to set up your local development environment.

## Overview

By the end of this tutorial, you will have:

1. A new `ingestion/acme_api/` package with a `Puller` subclass
2. A working CLI command: `ingestion acme_api pull --start ... --end ...`
3. Unit tests that mock the API client
4. Optional dependencies in `pyproject.toml`
5. The source added to the devcontainer for local testing

## 1. Create the Source Package

Start by creating the package structure:

```bash
mkdir -p ingestion/acme_api
touch ingestion/acme_api/__init__.py
touch ingestion/acme_api/pull.py
```

The package structure:

```
ingestion/acme_api/
├── __init__.py      # Empty or re-exports (optional)
└── pull.py          # Contains the Puller subclass
```

## 2. Implement the Puller

Create `ingestion/acme_api/pull.py`:

```python
"""Acme API puller — fetches widget data from the Acme API."""

import pandas as pd

from ingestion.base.pull import Puller
from ingestion.base.gcs import upload_to_storage

FILENAME = "widgets.csv"


def fetch_widgets(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch widget data from the Acme API.

    This is a contrived example. In a real implementation, you would
    use an actual API client or make HTTP requests here.

    Args:
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    Returns:
        DataFrame with raw widget data.
    """
    # Mock data for demonstration
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Widget A", "Widget B", "Widget C"],
        "created_at": [start_date, start_date, end_date],
    })


class AcmeApiPuller(Puller):
    """Pull data from the Acme API.

    Fetches widget data and uploads it to GCS (or local filesystem).
    """

    source_name = "acme_api"

    def pull(
        self,
        source: str,
        start_date: str | None = None,
        end_date: str | None = None,
        bucket_name: str | None = None,
    ) -> list[str]:
        """Pull Acme API data for the given date range.

        Args:
            source: Source name (used for path prefix).
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            bucket_name: GCS bucket name (overrides BUCKET_NAME env var).

        Returns:
            List of uploaded file paths.
        """
        paths = []

        # Fetch data from the API
        df = fetch_widgets(start_date, end_date)
        csv_data = df.to_csv(index=False)

        # Upload to storage
        path = upload_to_storage(
            data=csv_data,
            source=source,
            filename=FILENAME,
            pull_date=start_date,
            bucket_name=bucket_name,
        )
        paths.append(path)

        return paths
```

### Key Points

- **`source_name`**: This class attribute identifies the source. It determines the CLI subcommand (`ingestion acme_api pull`) and the GCS path prefix.
- **Auto-discovery**: The framework discovers all `Puller` subclasses at import time — no manual registration needed.
- **`bucket_name`**: The optional bucket parameter lets callers override the `BUCKET_NAME` environment variable directly from the CLI.

## 3. Add Optional Dependencies

If the source required additional packages (e.g., an Acme API SDK), add them to `pyproject.toml`:

```toml
[project.optional-dependencies]
acme_api = [
    "acme-sdk>=1.0",
]
```

Add `acme_api` to the setuptools packages list:

```toml
[tool.setuptools]
packages = ["ingestion", "ingestion.base", "ingestion.toggl", "ingestion.acme_api"]
```

> **Note**: For this tutorial, we do not add external dependencies since we are using mock data. But in a real implementation, you would include the SDK here.

Update the devcontainer to install the new source:

```dockerfile
RUN pip install .[toggl,acme_api]
```

## 4. Write Unit Tests

Create `tests/ingestion/acme_api/test_pull.py`:

```python
"""Tests for Acme API puller."""

from unittest.mock import patch

import pandas as pd
import pytest

from ingestion.acme_api.pull import AcmeApiPuller, fetch_widgets


class TestFetchWidgets:
    """Tests for the fetch_widgets function."""

    def test_fetch_widgets_returns_dataframe(self):
        """Test that fetch_widgets returns a DataFrame."""
        result = fetch_widgets("2026-10-01", "2026-10-31")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "id" in result.columns
        assert "name" in result.columns

    def test_fetch_widgets_uses_date_range(self):
        """Test that the returned data reflects the date range."""
        result = fetch_widgets("2026-10-01", "2026-10-31")
        assert result["created_at"].iloc[0] == "2026-10-01"
        assert result["created_at"].iloc[-1] == "2026-10-31"


class TestAcmeApiPuller:
    """Tests for the AcmeApiPuller class."""

    def test_puller_has_source_name(self):
        """Test that the puller defines source_name."""
        assert AcmeApiPuller.source_name == "acme_api"

    def test_pull_uses_correct_filename(self):
        """Test that pull uploads with the expected filename."""
        with patch("ingestion.acme_api.pull.upload_to_storage") as mock_upload:
            mock_upload.return_value = "compiler-data-lake/acme_api/2026/10/01/widgets_20261001T000000.csv"

            puller = AcmeApiPuller()
            puller.pull("acme_api", "2026-10-01", "2026-10-31")

            mock_upload.assert_called_once()
            call_args = mock_upload.call_args
            assert call_args[1]["filename"] == "widgets.csv"

    def test_pull_returns_single_path(self):
        """Test that pull returns one path for the single widget file."""
        with patch("ingestion.acme_api.pull.upload_to_storage") as mock_upload:
            mock_upload.return_value = "compiler-data-lake/acme_api/2026/10/01/widgets_20261001T000000.csv"

            puller = AcmeApiPuller()
            paths = puller.pull("acme_api", "2026-10-01", "2026-10-31")

            assert len(paths) == 1

    def test_pull_passes_pull_date(self):
        """Test that pull_date is passed to upload_to_storage."""
        with patch("ingestion.acme_api.pull.upload_to_storage") as mock_upload:
            mock_upload.return_value = "compiler-data-lake/acme_api/2026/10/01/widgets_20261001T000000.csv"

            puller = AcmeApiPuller()
            puller.pull("acme_api", "2026-10-01", "2026-10-31")

            call_args = mock_upload.call_args
            assert call_args[1]["pull_date"] == "2026-10-01"

    def test_pull_passes_bucket_name(self):
        """Test that bucket_name is forwarded to upload_to_storage."""
        with patch("ingestion.acme_api.pull.upload_to_storage") as mock_upload:
            mock_upload.return_value = "compiler-data-lake/acme_api/2026/10/01/widgets_20261001T000000.csv"

            puller = AcmeApiPuller()
            puller.pull("acme_api", "2026-10-01", "2026-10-31", bucket_name="test-bucket")

            call_args = mock_upload.call_args
            assert call_args[1]["bucket_name"] == "test-bucket"
```

Run the tests:

```bash
pytest tests/ingestion/acme_api/ -v
```

### Test Patterns

The test patterns used here follow the same approach as the existing Toggl tests:

| Pattern                 | Technique                                                    | Purpose                                                                            |
| ----------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **Mock uploads**        | `patch("ingestion.acme_api.pull.upload_to_storage")`         | Verify `upload_to_storage()` is called with correct arguments without touching GCS |
| **Mock API**            | Direct function calls (no mock needed for contrived example) | In real code, mock HTTP clients or subprocess calls                                |
| **Assertion on kwargs** | `call_args[1]["pull_date"]`                                  | Verify keyword arguments are forwarded correctly                                   |

## 5. Verify and Test Locally

The new source should be discovered automatically by the CLI. Verify with:

```bash
# Check the source is registered
ingestion acme_api pull --help

# Expected output:
# Usage: ingestion acme_api pull [OPTIONS] action
#
#   Pull data for the given date range.
#
# Options:
#   --start TEXT    Start date (absolute or relative keyword)
#   --end TEXT      End date (absolute or relative keyword)
#   --bucket TEXT   GCS bucket name (overrides BUCKET_NAME env var)
#   --help          Show this message and exit.
```

Run a test pull without GCP credentials (uses local filesystem mode):

```bash
ingestion acme_api pull --start 2026-10-01 --end 2026-10-31
```

Check the output:

```bash
ls -la /tmp/warehouse-ingestion/acme_api/
```

The files will be written to `/tmp/warehouse-ingestion/` when no bucket is specified.

To test with GCS, use the `--bucket` flag:

```bash
ingestion acme_api pull --start 2026-10-01 --end 2026-10-31 --bucket compiler-data-lake
```

## 6. Prepare Infrastructure

Before you can deploy, you need to define the production resources: the Terraform module, the Docker image, the CI/CD build step, and the secrets.

### 1. Create the Terraform Module

Create `terraform/modules/ingestion/acme_api/` with these files:

**`variables.tf`** — inputs to the module:

```hcl
variable "project_id" {
  description = "The GCP project ID in which to create resources."
  type        = string
}

variable "region" {
  description = "The GCP region for the Cloud Run job and Cloud Scheduler job."
  type        = string
  default     = "us-west1"
}

variable "image_tag" {
  description = "Docker image tag for the ingestion job (GHCR)."
  type        = string
}

variable "output_bucket" {
  description = "GCS bucket name for output files."
  type        = string
}

variable "ingestion_service_account_id" {
  description = "Email of the Cloud Run job service account."
  type        = string
}
```

**`main.tf`** — Cloud Run Job and Cloud Scheduler:

```hcl
locals {
  job_name = "ingestion-acme-api"
}

# ─── Cloud Run Job ───────────────────────────────────────────────────────────

resource "google_cloud_run_v2_job" "ingestion" {
  name                = local.job_name
  location            = var.region
  project             = var.project_id
  deletion_protection = false

  template {
    parallelism = 1
    task_count  = 1

    template {
      service_account = var.ingestion_service_account_id
      max_retries     = 1

      containers {
        name  = "ingestion"
        image = "ghcr.io/compilerla/warehouse/ingestion/acme_api:${var.image_tag}"

        args = ["acme_api", "pull", "--start", "last-month", "--end", "yesterday"]

        resources {
          limits = {
            cpu    = "0.25"
            memory = "256Mi"
          }
        }
      }
    }
  }
}

# ─── Cloud Scheduler Job ─────────────────────────────────────────────────────

resource "google_cloud_scheduler_job" "ingestion" {
  name             = "${local.job_name}-daily"
  description      = "Daily pull of the previous calendar month from Acme API."
  schedule         = "0 6 * * *"
  time_zone        = "America/Los_Angeles"
  project          = var.project_id
  region           = var.region
  attempt_deadline = "300s"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-cloudrun.googleapis.com/v2/${google_cloud_run_v2_job.ingestion.name}:run"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({
      "template" = {
        "template" = {
          "containers" = [
            {
              "args" = [
                "acme_api",
                "pull",
                "--start", "last-month",
                "--end", "yesterday",
              ]
            }
          ]
        }
      }
    }))

    oidc_token {
      service_account_email = var.ingestion_service_account_id
      audience              = "https://${var.region}-cloudrun.googleapis.com/v2/${google_cloud_run_v2_job.ingestion.name}:run"
    }
  }
}
```

**`iam.tf`** — IAM bindings for the service account:

```hcl
# Allow the Cloud Run job service account to write objects to the output bucket.
resource "google_storage_bucket_iam_member" "object_creator" {
  bucket = var.output_bucket
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${var.ingestion_service_account_id}"
}

# Allow the Cloud Run job service account to read secrets at runtime.
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${var.ingestion_service_account_id}"
}
```

**`outputs.tf`** — values to expose from the module:

```hcl
output "job_name" {
  description = "Name of the Cloud Run job."
  value       = google_cloud_run_v2_job.ingestion.name
}

output "scheduler_name" {
  description = "Name of the Cloud Scheduler job."
  value       = google_cloud_scheduler_job.ingestion.name
}
```

### 2. Create the Dockerfile

Each ingestion source gets its own Dockerfile that extends the base image and sets its own `ENTRYPOINT`. The base image (`Dockerfile.base`) handles the wheel build in stage 1 and installs it in stage 2 (without extras). The source image extends the base and installs only its own extras.

Create `ingestion/Dockerfile.acme_api`:

```dockerfile
ARG PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USER=compiler \
    USER_UID=1000 \
    USER_GID=1000

FROM ghcr.io/compilerla/warehouse/ingestion/base:latest

ARG USER_UID \
    USER_GID

ARG IMAGE_VERSION
ARG IMAGE_CREATED

LABEL org.opencontainers.image.version="${IMAGE_VERSION}"
LABEL org.opencontainers.image.created="${IMAGE_CREATED}"
LABEL org.opencontainers.image.url="ghcr.io/compilerla/warehouse/ingestion/acme_api"

# USER_UID / USER_GID are not inherited as ENV from base (base only sets them as ARG),
# but they are needed for BuildKit --mount uid/gid resolution at build time.
# All other ENV vars (PYTHONUNBUFFERED, HOME, USER, PATH, etc.) are inherited
# from the base image's ENV and need no re-declaration.

USER root
RUN --mount=type=cache,id=apt-archives,sharing=locked,target=/var/cache/apt/archives \
    --mount=type=cache,id=apt-lists,sharing=locked,target=/var/lib/apt/lists \
    apt-get update && \
    apt-get install --only-upgrade -y ca-certificates && \
    update-ca-certificates
USER ${USER}

# install acme_api extras on top of the base image's installed wheel
RUN --mount=type=cache,id=pipcache,target=${PIP_CACHE_DIR},uid=${USER_UID},gid=${USER_GID} \
    python -m pip install --user --upgrade pip && \
    pip install --user $(find /opt/wheels -name '*.whl')[acme_api]

ENTRYPOINT ["ingestion", "acme_api", "pull"]
```

> **No extras needed?** If the source uses only the base dependencies (click, pandas, google-cloud-storage, etc.), omit the `[acme_api]` extra from the pip install line — the base image already has everything.
>
> **Source-specific extras**: If you declared `acme_api = [...]` in `pyproject.toml` (step 3), reference it with `[acme_api]`. This installs only the source-specific packages on top of the base image's common dependencies.

### 3. Create Secrets

Create the secrets that the job needs at runtime:

```bash
gcloud secrets create acme-api-token \
  --data-from-file=- \
  --replication-policy=automatic \
  --project=data-warehouse-492522
# (paste your token, press Ctrl+D)
```

Add a data source to read it (create `secrets.tf` in the module):

```hcl
data "google_secret_manager_secret_version" "acme_api_token" {
  secret = "acme-api-token"
}
```

And reference it in the container env in `main.tf`:

```hcl
env {
  name = "ACME_API_TOKEN"
  value_source {
    secret_key_ref {
      secret  = data.google_secret_manager_secret_version.acme_api_token.secret
      version = "latest"
    }
  }
}
```

### 4. Add the CI/CD Build Step

The deploy workflow builds images per-source. Each source needs its own `Dockerfile` and a build step in `.github/workflows/deploy.yml`.

**Add the build step** to the `build-images` job, alongside the existing toggl step:

```yaml
- name: Build & push ingestion acme_api image
  uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0
  with:
    context: .
    file: ingestion/Dockerfile.acme_api
    push: true
    tags: |
      ghcr.io/compilerla/warehouse/ingestion/acme_api:${{ env.TOGGL_IMAGE_TAG }}
      ghcr.io/compilerla/warehouse/ingestion/acme_api:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
    build-args: |
      IMAGE_CREATED=${{ env.IMAGE_CREATED }}
      IMAGE_VERSION=${{ env.IMAGE_VERSION }}
```

> **Image tag**: The workflow currently uses `TOGGL_IMAGE_TAG` for all ingestion images. For a new source that shares the same release cadence, reuse this variable. If the source needs independent releases, add a new input like `ingestion_acme_api_image_tag` to the `workflow_dispatch` trigger and a corresponding `env` variable.

**Add the Terraform variable** to `terraform/terraform.tfvars` (or your preferred variable file):

```hcl
ingestion_acme_api_image_tag = "abc1234"
```

> **Root variables**: `terraform.tfvars` defines the runtime values Terraform uses. The `var.*` declarations in `variables.tf` at the root of `terraform/` define the types and defaults. Add `variable "ingestion_acme_api_image_tag" { type = string }` to `terraform/variables.tf` if it doesn't already exist.

### 5. Wire the Module into Root Config

Add the module to `terraform/main.tf`:

```hcl
module "ingestion-acme-api" {
  source = "./modules/ingestion/acme_api"

  project_id                   = var.project_id
  region                       = var.region
  image_tag                    = var.ingestion_acme_api_image_tag
  output_bucket                = module.storage.bucket_name
  ingestion_service_account_id = module.iam.ingestion_service_account_email

  depends_on = [module.apis, module.iam, module.storage]
}
```

### 6. Apply Infrastructure

```bash
cd terraform
terraform init
terraform plan -lock-timeout=5m
terraform apply -lock-timeout=5m tfplan
```

After apply, the Cloud Run Job and Cloud Scheduler exist but won't run yet — they need a deployed image.

## 7. Deploy to Production

With all the infrastructure in place, push a release tag to trigger the CI/CD workflow. The pipeline will:

1. Build and push the `ingestion/acme_api` Docker image to GHCR
2. Plan and apply the Terraform changes (binding the image tag to the Cloud Run Job)
3. Run the health check on the deployed job
4. Create a GitHub Release

Trigger the pipeline:

```bash
git tag -a 2026.11.20
git push origin 2026.11.20
```

Watch the run in [GitHub Actions](https://github.com/compilerla/warehouse/actions):

```bash
gh run list --repo compilerla/warehouse --workflow Deploy --json title,displayStatus,createdAt | jq '.'
```

Verify the deployment by checking the Cloud Run Job ran successfully:

```bash
gcloud run jobs describe ingestion-acme-api \
  --region us-west1 \
  --project data-warehouse-492522
```

And confirm data landed in GCS:

```bash
gsutil ls gs://compiler-data-lake/acme_api/
```

## Checklist

- [ ] Created `ingestion/acme_api/pull.py` with a `Puller` subclass
- [ ] Set `source_name = "acme_api"`
- [ ] `pull()` returns `list[str]` of uploaded file paths
- [ ] Added `acme_api` to `pyproject.toml` optional dependencies (if needed)
- [ ] Added `acme_api` to `[tool.setuptools].packages`
- [ ] Added `acme_api` to devcontainer pip install
- [ ] Created `tests/ingestion/acme_api/test_pull.py` with unit tests
- [ ] Tested locally (`ingestion acme_api pull --start ... --end ...`)
- [ ] Created `Dockerfile.acme_api` with `ENTRYPOINT ["ingestion", "acme_api", "pull"]`
- [ ] Added CI/CD build step to `.github/workflows/deploy.yml`
- [ ] Added `ingestion_acme_api_image_tag` to `terraform/variables.tf` and `terraform.tfvars`
- [ ] Added Cloud Run Job, Scheduler, and IAM in Terraform
- [ ] Pushed release tag and verified the deployment

## What's Next

- See the [Adding an Ingestion Source](../guides/adding-ingestion-source.md) guide for a more detailed walkthrough with secrets handling, Terraform infrastructure, and deployment considerations.
- See the [Ingestion Operations Guide](../guides/ingestion-operations.md) for monitoring, troubleshooting, and ad-hoc pull procedures.
- See the [Deploying to Production](../explanation/deployment-production.md) guide for a detailed explanation of the CI/CD pipeline.
