# Allow the dbt runner Cloud Run job to create and update BigQuery tables.
resource "google_project_iam_member" "dbt_runner_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${var.dbt_service_account_id}"
}

# Allow the dbt runner Cloud Run job to run queries in BigQuery.
resource "google_project_iam_member" "dbt_runner_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${var.dbt_service_account_id}"
}
