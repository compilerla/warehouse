variable "project_id" {
  description = "The GCP project ID in which to create resources."
  type        = string
}

variable "region" {
  description = "The GCP region for the Cloud Run job and Cloud Scheduler job."
  type        = string
  default     = "us-west1"
}

variable "image_tag" {
  description = "Docker image tag for the ingestion job (GHCR)."
  type        = string
}

variable "output_bucket" {
  description = "GCS bucket name for output files."
  type        = string
}

variable "ingestion_service_account_id" {
  description = "Email of the Cloud Run job service account."
  type        = string
}
