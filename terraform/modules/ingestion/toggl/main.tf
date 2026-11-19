locals {
  job_name = "ingestion-toggl"
}

# ─── Cloud Run Job ───────────────────────────────────────────────────────────
# Runs `ingestion toggl pull` daily. The Cloud Scheduler job passes --start
# last-month --end yesterday as arguments, which the Python CLI resolves
# at runtime to the actual date range for that execution.

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
        image = "ghcr.io/compilerla/warehouse/ingestion/toggl:${var.image_tag}"

        args = ["--all"]

        resources {
          limits = {
            cpu    = "0.25"
            memory = "256Mi"
          }
        }

        env {
          name = "TOGGL_API_TOKEN"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret_version.toggl_api_token.secret
              version = "latest"
            }
          }
        }

        env {
          name = "TOGGL_WORKSPACE_ID"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret_version.toggl_workspace_id.secret
              version = "latest"
            }
          }
        }

        env {
          name = "TOGGL_ORGANIZATION_ID"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret_version.toggl_organization_id.secret
              version = "latest"
            }
          }
        }
      }
    }
  }
}

# ─── Cloud Scheduler Job ─────────────────────────────────────────────────────
# Single scheduler triggers the job daily with relative date keywords.
# The CLI resolves "last-month" and "yesterday" at runtime.

resource "google_cloud_scheduler_job" "ingestion" {
  name             = "${local.job_name}-daily"
  description      = "Daily pull of the previous calendar month for end-of-month re-classification and dashboard freshness."
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

    # Pass relative date keywords — resolved by the CLI at runtime.
    # Example: on Nov 18, this pulls Oct 1 – Nov 17.
    body = base64encode(jsonencode({
      "template" = {
        "template" = {
          "containers" = [
            {
              "args" = [
                "--all",
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
