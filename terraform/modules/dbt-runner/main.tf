locals {
  job_name = "dbt-runner"
}

# ─── Cloud Run Job ───────────────────────────────────────────────────────────
# Runs `dbt run` to transform external tables in BigQuery into base/mart
# reporting tables. Triggered by Cloud Scheduler on a schedule or by GitHub
# Actions for ad-hoc runs.

resource "google_cloud_run_v2_job" "dbt_runner" {
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
        name  = "dbt"
        image = "ghcr.io/compilerla/warehouse/dbt:${var.image_tag}"

        command = ["dbt", "run", "--profiles-dir", "/root/.dbt"]

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

        env {
          name  = "DBT_PROFILES_DIR"
          value = "/root/.dbt"
        }

        env {
          name  = "DBT_TARGET"
          value = "prod"
        }

        env {
          name  = "DBT_LOG_FORMAT"
          value = "json"
        }
      }
    }
  }
}

# ─── Cloud Scheduler Job ─────────────────────────────────────────────────────
# Triggers the dbt runner daily after external tables are refreshed.

resource "google_cloud_scheduler_job" "dbt_runner" {
  name             = "${local.job_name}-daily"
  description      = "Daily dbt transformation run after external tables refresh."
  schedule         = "0 4 * * *"
  time_zone        = "America/Los_Angeles"
  project          = var.project_id
  region           = var.region
  attempt_deadline = "300s"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-cloudrun.googleapis.com/v2/${google_cloud_run_v2_job.dbt_runner.name}:run"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({
      "template" = {
        "template" = {
          "containers" = [
            {
              "args" = [
                "dbt", "run", "--profiles-dir", "/root/.dbt"
              ]
            }
          ]
        }
      }
    }))

    oidc_token {
      service_account_email = var.dbt_service_account_id
      audience              = "https://${var.region}-cloudrun.googleapis.com/v2/${google_cloud_run_v2_job.dbt_runner.name}:run"
    }
  }
}
