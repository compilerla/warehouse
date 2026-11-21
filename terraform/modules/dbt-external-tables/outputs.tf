output "job_name" {
  description = "Name of the Cloud Run job."
  value       = google_cloud_run_v2_job.external_tables.name
}

output "scheduler_name" {
  description = "Name of the Cloud Scheduler job."
  value       = google_cloud_scheduler_job.external_tables.name
}
