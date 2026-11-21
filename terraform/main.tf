module "apis" {
  source = "./modules/apis"

  project_id = var.project_id
}

module "iam" {
  source = "./modules/iam"

  project_id = var.project_id

  depends_on = [module.apis]
}

module "wif" {
  source = "./modules/wif"

  project_id         = var.project_id
  service_account_id = module.iam.github_actions_service_account_id
  pool_id            = "github-actions-pool-01"
  provider_id        = "github-actions-provider-01"

  depends_on = [module.iam]
}

module "bigquery" {
  source = "./modules/bigquery"

  metabase_service_account_email = module.iam.metabase_service_account_email
  project_id                     = var.project_id

  depends_on = [module.apis, module.iam]
}

module "database" {
  source = "./modules/database"

  project_id          = var.project_id
  region              = var.region
  deletion_protection = var.deletion_protection

  depends_on = [module.apis]
}

module "storage" {
  source = "./modules/storage"

  project_id = var.project_id
  location   = var.region
}

module "metabase" {
  source = "./modules/metabase"

  cloud_sql_connection_name = module.database.connection_name
  container_image_tag       = var.metabase_image_tag
  database_name             = module.database.database_name
  database_user             = module.database.database_user
  project_id                = var.project_id
  region                    = var.region
  service_account_email     = module.iam.metabase_service_account_email
  google_client_id          = var.google_client_id
  smtp_password             = var.smtp_password
  deletion_protection       = var.deletion_protection

  depends_on = [module.apis, module.iam, module.database]
}

module "ingestion-toggl" {
  source = "./modules/ingestion/toggl"

  project_id                   = var.project_id
  region                       = var.region
  image_tag                    = var.ingestion_toggl_image_tag
  output_bucket                = module.storage.bucket_name
  ingestion_service_account_id = module.iam.ingestion_service_account_email

  depends_on = [module.apis, module.iam, module.storage]
}

module "dbt-runner" {
  source = "./modules/dbt-runner"

  project_id             = var.project_id
  region                 = var.region
  image_tag              = var.dbt_image_tag
  dbt_service_account_id = module.iam.dbt_runner_service_account_email

  depends_on = [module.apis, module.iam, module.bigquery]
}

module "dbt-external-tables" {
  source = "./modules/dbt-external-tables"

  project_id             = var.project_id
  region                 = var.region
  image_tag              = var.dbt_image_tag
  dbt_service_account_id = module.iam.dbt_runner_service_account_email

  depends_on = [module.apis, module.iam, module.bigquery, module.storage]
}
