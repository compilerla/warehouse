# Ingestion Operations

This guide covers operational procedures for the ingestion framework: monitoring, troubleshooting, and ad-hoc pulls.

> **Adding a new source?** See the [Adding an Ingestion Source](adding-ingestion-source.md) guide for a step-by-step walkthrough.

## Monitoring Cloud Run Jobs

### View Job Status

```bash
gcloud run jobs describe ingestion-toggl \
  --project=data-warehouse-492522 \
  --region=us-west1
```

### List Recent Executions

```bash
gcloud run jobs executions list \
  --job=ingestion-toggl \
  --project=data-warehouse-492522 \
  --region=us-west1
```

### View Job Logs

```bash
# View logs for the most recent execution
gcloud run jobs executions logs \
  --job=ingestion-toggl \
  --project=data-warehouse-492522 \
  --region=us-west1

# Filter by execution name
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=ingestion-toggl" \
  --project=data-warehouse-492522 \
  --limit=50
```

## Reviewing Ingestion Logs

The `ingestion-toggl` job logs stdout and stderr. Key log patterns to look for:

```
[TIMESHEETS] stderr: ...   # Subprocess output from compiler-admin
[USERS] stderr: ...
[PROJECTS] stderr: ...
[CLIENTS] stderr: ...
[PROJECT-USERS] stderr: ...
```

Each data source (timesheets, users, clients, projects, project users) logs its subprocess output separately.

## Triggering Ad-Hoc Pulls

To manually trigger an ingestion pull outside the scheduled daily run:

```bash
# Pull last week's data
gcloud run jobs execute ingestion-toggl \
  --project=data-warehouse-492522 \
  --region=us-west1 \
  --argument='--start' \
  --argument='last-week' \
  --argument='--end' \
  --argument='yesterday'
```

Or use absolute dates:

```bash
gcloud run jobs execute ingestion-toggl \
  --project=data-warehouse-492522 \
  --region=us-west1 \
  --argument='--start' \
  --argument='2026-10-01' \
  --argument='--end' \
  --argument='2026-10-31'
```

## Troubleshooting Failed Pulls

### Job Fails to Start

1. Check the service account permissions:

   ```bash
   gcloud run jobs describe ingestion-toggl \
     --project=data-warehouse-492522 \
     --region=us-west1
   ```

   Ensure the service account (`ingestion-runner@...`) has:
   - `roles/storage.objectCreator` on `compiler-data-lake`
   - `roles/secretmanager.secretAccessor`

2. Verify secrets exist in Secret Manager:
   ```bash
   gcloud secrets versions access latest \
     --secret=toggl-api-token \
     --project=data-warehouse-492522
   ```

### Pull Returns Empty Data

1. Check the source system (e.g., Toggl) for the requested date range.
2. Verify the `compiler-admin` CLI is installed and accessible on PATH.
3. Review job logs for errors from `subprocess.run` calls.

### Upload Fails

1. Check bucket permissions — the service account needs `roles/storage.objectCreator` on `compiler-data-lake`.
2. Verify the GCS bucket exists:
   ```bash
   gsutil ls gs://compiler-data-lake/
   ```

### Date Resolution Errors

The CLI validates that `start_date` is not after `end_date`. If you see a validation error:

```
ValueError: Start date (2026-10-31) is after end date (2026-10-01)
```

Use consistent keywords or explicit date ranges:

```bash
# Good: consistent keywords
--start last-month --end yesterday

# Good: explicit dates
--start 2026-10-01 --end 2026-10-31

# Bad: mismatched
--start last-month --end 2026-10-01
```

## Adding a New Source

For a detailed walkthrough of adding a new ingestion source, see the [Adding an Ingestion Source](adding-ingestion-source.md) guide.
