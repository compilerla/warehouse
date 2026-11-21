variable "dataset_default_partition_expiration_ms" {
  default     = null
  description = "Default partition expiration in milliseconds for all datasets. Null means no expiration."
  type        = number
}

variable "datasets" {
  description = "Map of BigQuery datasets to create. Key is the dataset ID."
  type = map(object({
    description                     = string
    default_partition_expiration_ms = optional(number)
    delete_contents_on_destroy      = optional(bool, false)
  }))
  default = {
    raw = {
      description                = "External tables reading raw data directly from GCS (CSV/JSONL)."
      delete_contents_on_destroy = false
    }
    base = {
      description                = "Base-layer transformation tables produced by dbt from external tables."
      delete_contents_on_destroy = false
    }
    mart = {
      description                = "Mart-layer reporting tables produced by dbt, queried by Metabase."
      delete_contents_on_destroy = false
    }
  }
}

variable "location" {
  description = "The BigQuery geographic location for all datasets (e.g. US, EU, us-west1)."
  type        = string
  default     = "US"
}

variable "metabase_service_account_email" {
  description = "The email of the Metabase Cloud Run service account, granted read access to all datasets."
  type        = string
}

variable "project_id" {
  description = "The GCP project ID in which to create BigQuery datasets."
  type        = string
}
