# Allow the Cloud Run job service account to write objects to the output bucket.
resource "google_storage_bucket_iam_member" "object_creator" {
  bucket = var.output_bucket
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${var.ingestion_service_account_id}"
}

# Allow the Cloud Run job service account to read secrets at runtime.
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${var.ingestion_service_account_id}"
}
