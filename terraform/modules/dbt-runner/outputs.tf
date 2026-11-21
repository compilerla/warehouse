output "job_name" {
  description = "Name of the Cloud Run job."
  value       = google_cloud_run_v2_job.dbt_runner.name
}

output "scheduler_name" {
  description = "Name of the Cloud Scheduler job."
  value       = google_cloud_scheduler_job.dbt_runner.name
}
