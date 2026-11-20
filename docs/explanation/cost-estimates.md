# Production Cost Estimates

This page provides an initial monthly pricing estimate for the production environment of the Warehouse project. These figures are based on minimal production-ready configurations and low request volumes.

## Monthly Estimated Cost Breakdown

| Resource                      | Configuration                              | Estimated Monthly Cost |
| :---------------------------- | :----------------------------------------- | :--------------------- |
| **Cloud SQL (PostgreSQL)**    | 2 vCPU, 7.5 GB RAM, 10 GB SSD              | $60 – $90              |
| **Cloud Run (Metabase)**      | Min instances = 1, Low volume              | $10 – $30              |
| **Cloud Run Job (ingestion)** | 0.25 vCPU, 256 MiB, 1 execution/day        | $0 – $2                |
| **Cloud Scheduler**           | 1 job (daily), Low volume                  | $0 – $1                |
| **BigQuery**                  | Dataset only, minimal queries              | $0 – $5                |
| **GCS Storage**               | < 1 GB total                               | $0 – $1                |
| **Secret Manager**            | 5 secrets (Metabase + Toggl tokens)        | $0 – $1                |
| **Total Estimated Monthly**   |                                            | **$71 – $130**         |

## Key Assumptions & Notes

- **Cloud SQL**: Sized for a small team (approx. 20 users) to ensure smooth performance for Metabase metadata operations.
- **Cloud Run**: Includes a minimum of 1 instance to eliminate "cold start" delays for users.
- **Cloud Run Job**: The ingestion job runs once daily with minimal resources (0.25 vCPU, 256 MiB). Jobs are pay-per-execution, so costs are negligible at low frequency.
- **Cloud Scheduler**: Triggers the ingestion job daily. Costs are based on a single low-frequency job.
- **BigQuery**: Currently configured as a dataset with viewer access for Metabase. No compute queries have been run yet.
- **Secret Manager**: Stores Metabase credentials (DB password, encryption key) and Toggl API credentials (api_token, workspace_id, organization_id). Free tier covers up to 100 secrets.
- **GCS Storage**: Currently ingests ~333 KB/month. Costs are expected to remain negligible until data volume scales significantly.
- **Variability**: These are estimates. Actual costs may fluctuate based on specific usage patterns and GCP pricing updates in the `us-west1` region.
