locals {
  job_name = "dbt-external-tables"
}

# ─── Cloud Run Job ───────────────────────────────────────────────────────────
# Manages BigQuery external tables that point at GCS files. Reads YAML config
# files from the dbt package, creates or updates external tables in the raw
# dataset. Triggered by Cloud Scheduler after ingestion completes.

resource "google_cloud_run_v2_job" "external_tables" {
  name                = local.job_name
  location            = var.region
  project             = var.project_id
  deletion_protection = false

  template {
    parallelism = 1
    task_count  = 1

    template {
      service_account = var.dbt_service_account_id
      max_retries     = 1

      containers {
        name  = "external-tables"
        image = "ghcr.io/compilerla/warehouse/dbt:${var.image_tag}"

        command = ["python", "-m", "dbt.external_tables.manage", "--all"]

        resources {
          limits = {
            cpu    = "0.5"
            memory = "512Mi"
          }
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
      }
    }
  }
}

# ─── Cloud Scheduler Job ─────────────────────────────────────────────────────
# Triggers external table refresh daily, after ingestion completes and before
# the dbt runner kicks off transformations.

resource "google_cloud_scheduler_job" "external_tables" {
  name             = "${local.job_name}-daily"
  description      = "Daily refresh of BigQuery external tables from GCS source paths."
  schedule         = "0 3 * * *"
  time_zone        = "America/Los_Angeles"
  project          = var.project_id
  region           = var.region
  attempt_deadline = "300s"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-cloudrun.googleapis.com/v2/${google_cloud_run_v2_job.external_tables.name}:run"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({
      "template" = {
        "template" = {
          "containers" = [
            {
              "args" = [
                "python", "-m", "dbt.external_tables.manage", "--all"
              ]
            }
          ]
        }
      }
    }))

    oidc_token {
      service_account_email = var.dbt_service_account_id
      audience              = "https://${var.region}-cloudrun.googleapis.com/v2/${google_cloud_run_v2_job.external_tables.name}:run"
    }
  }
}
