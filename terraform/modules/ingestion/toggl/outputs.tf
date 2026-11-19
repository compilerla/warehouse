output "job_name" {
  description = "Name of the Cloud Run job."
  value       = google_cloud_run_v2_job.ingestion.name
}

output "scheduler_name" {
  description = "Name of the Cloud Scheduler job."
  value       = google_cloud_scheduler_job.ingestion.name
}

output "secret_ids" {
  description = "Secret Manager secret IDs consumed by the job."
  value = {
    toggl_api_token       = data.google_secret_manager_secret_version.toggl_api_token.secret
    toggl_workspace_id    = data.google_secret_manager_secret_version.toggl_workspace_id.secret
    toggl_organization_id = data.google_secret_manager_secret_version.toggl_organization_id.secret
  }
}
