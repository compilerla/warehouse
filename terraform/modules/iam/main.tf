
locals {
  # roles/bigquery.dataViewer is granted at the individual dataset level
  # by the bigquery module, so only jobUser is needed here at project level.
  metabase_roles = [
    "roles/bigquery.jobUser",
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor"
  ]

  # Roles for the CI/CD runner to manage infrastructure
  github_actions_roles = [
    "roles/editor",
    "roles/resourcemanager.projectIamAdmin",
    "roles/iam.serviceAccountTokenCreator"
  ]
}

resource "google_service_account" "metabase" {
  account_id   = var.service_account_id
  description  = "Dedicated runtime service account for Metabase on Cloud Run"
  display_name = "Metabase Cloud Run Service Account"
  project      = var.project_id
}

resource "google_service_account" "github_actions" {
  account_id   = "github-actions-runner"
  description  = "Service account for GitHub Actions CI/CD"
  display_name = "GitHub Actions Runner"
  project      = var.project_id
}

resource "google_service_account" "ingestion" {
  account_id   = "ingestion-runner"
  description  = "Dedicated runtime service account for ingestion Cloud Run Jobs"
  display_name = "Ingestion Cloud Run Service Account"
  project      = var.project_id
}

resource "google_service_account" "dbt_runner" {
  account_id   = "dbt-runner"
  description  = "Dedicated runtime service account for dbt Cloud Run Jobs (external tables + transformations)"
  display_name = "DBT Cloud Run Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "metabase_roles" {
  for_each = toset(local.metabase_roles)

  member  = "serviceAccount:${google_service_account.metabase.email}"
  project = var.project_id
  role    = each.value
}

resource "google_project_iam_member" "github_actions_roles" {
  for_each = toset(local.github_actions_roles)

  member  = "serviceAccount:${google_service_account.github_actions.email}"
  project = var.project_id
  role    = each.value
}
