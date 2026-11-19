# Secrets are pre-created in GCP Secret Manager.
# Terraform reads them via data sources — no values pass through .tfvars or CI.
#
# To create secrets before first apply:
#   gcloud secrets create ingestion-toggl-api-token --data-from-file=-
#   gcloud secrets create ingestion-toggl-workspace-id --data-from-file=-
#   gcloud secrets create ingestion-toggl-organization-id --data-from-file=-
#   # (paste value, Ctrl+D)
#
# For more on managing secrets: see docs/guides/ingestion-operations.md

data "google_secret_manager_secret_version" "toggl_api_token" {
  secret = "ingestion-toggl-api-token"
}

data "google_secret_manager_secret_version" "toggl_workspace_id" {
  secret = "ingestion-toggl-workspace-id"
}

data "google_secret_manager_secret_version" "toggl_organization_id" {
  secret = "ingestion-toggl-organization-id"
}
