# Repository Structure

```text
.
├── .devcontainer/
│   ├── devcontainer.json            # VS Code dev container definition
│   ├── Dockerfile                   # Dev container image (Terraform, gcloud, pre-commit)
│   └── postCreate.sh                # Container initialization & hook setup
├── .github/
│   └── workflows/                   # GitHub Actions for Terraform automation
├── bin/                             # Helper bash scripts for inside the dev container
│   ├── psql.sh                      # Connect to local PostgreSQL
│   └── wait-for-metabase.sh         # Health check waiter
├── docs/                            # MkDocs documentation site
│   ├── index.md                     # Documentation index
│   ├── explanation/                 # Architecture & design rationale
│   ├── guides/                      # How-to guides
│   ├── reference/                   # Technical reference docs
│   └── tutorials/                   # Step-by-step tutorials
├── ingestion/                       # Data ingestion framework (Puller abstraction, CLI, GCS upload)
│   ├── __init__.py                  # Package init; re-exports Puller, discover_pullers, etc.
│   ├── main.py                      # CLI entry point (Click); auto-discovers Puller subclasses
│   ├── Dockerfile.base              # Base image: Python 3.14 + system deps (python:3.14-trixie)
│   ├── Dockerfile.toggl             # Toggl-specific image: extends base, installs compiler-admin
│   ├── base/                        # Shared ingestion framework
│   │   ├── __init__.py              # Public API exports
│   │   ├── cli.py                   # CLI helpers: date range resolution (absolute, relative keywords)
│   │   ├── gcs.py                   # Upload to GCS or local filesystem with pull_date injection
│   │   ├── pull.py                  # Puller base class; PullConfig dataclass; auto-discovery
│   │   └── secrets.py               # Secret resolution from environment variables
│   ├── toggl/                       # Toggl timesheet ingestion source
│   │   ├── __init__.py              # Package init
│   │   └── pull.py                  # TogglPuller — fetches via compiler-admin CLI subprocess
│   └── tests/                       # Unit + integration tests
├── metabase/                        # Custom Metabase Docker image (Cloud SQL via socat)
│   ├── Dockerfile                   # Adds socat, sets custom entrypoint
│   └── entrypoint.sh                # Bridges Cloud SQL Unix socket → TCP 5432
├── terraform/                       # Infrastructure as Code (GCP Cloud Run & Cloud SQL)
│   ├── modules/                     # Reusable Terraform modules
│   │   ├── apis/                    # GCP API enablement
│   │   ├── bigquery/                # BigQuery datasets & IAM
│   │   ├── database/                # Cloud SQL PostgreSQL
│   │   ├── iam/                     # IAM service accounts & roles
│   │   ├── metabase/                # Cloud Run Metabase service
│   │   ├── secrets/                 # Secret Manager secrets
│   │   ├── storage/                 # GCS bucket
│   │   └── wif/                     # Workload Identity Federation
│   ├── main.tf                      # Root module (module assembly)
│   ├── variables.tf                 # Root variables
│   ├── outputs.tf                   # Root outputs
│   ├── providers.tf                 # Terraform provider config & GCS backend
│   └── terraform.tfvars             # Default variable values
├── .env.example                     # Sample local environment variables
├── .pre-commit-config.yaml          # Conventional commits & file hygiene hooks
├── compose.yml                      # Dev container service + local Metabase & Postgres
├── plan.md                          # Full architectural design & implementation plan
├── pyproject.toml                   # Python package config (click, pandas, gcloud-storage, pendulum)
└── README.md
```
