# Container Image Upgrade Procedure

This runbook covers how to upgrade container images on Cloud Run and Cloud Run Jobs via GitHub Actions CI/CD.

> **How the pipeline works**: See the [Deploying to Production](../explanation/deployment-production.md) guide for a detailed explanation of the workflow, build steps, and Terraform apply process.

## Current Configuration

### Metabase Service

| Setting        | Value                                         |
| -------------- | --------------------------------------------- |
| Service name   | metabase                                      |
| Region         | us-west1                                      |
| Image          | `ghcr.io/compilerla/warehouse/metabase:<sha>` |
| CPU limit      | 1 vCPU                                        |
| Memory limit   | 4 GiB                                         |
| Min instances  | 1                                             |
| Max instances  | 3                                             |
| Container port | 3000                                          |
| Cloud Run URL  | `https://metabase-2xhfhhdfxq-uw.a.run.app`    |

### Ingestion Job

| Setting          | Value                                                         |
| ---------------- | ------------------------------------------------------------- |
| Job name         | ingestion-toggl                                               |
| Region           | us-west1                                                      |
| Image            | `ghcr.io/compilerla/warehouse/ingestion/toggl:<sha>`          |
| CPU limit        | 0.25 vCPU                                                     |
| Memory limit     | 256 MiB                                                       |
| Max retries      | 1                                                             |
| Service Account  | `ingestion-runner@data-warehouse-492522.iam.gserviceaccount.com` |

## Prerequisites

- Push access to the `compilerla/warehouse` repository
- Write access to the `metabase/` directory (Dockerfile and entrypoint)
- Write access to the `ingestion/` directory (Dockerfiles and source code)

## Upgrade Procedure

### 1. Update the Metabase Image

Edit `metabase/Dockerfile` to change the base image version:

```dockerfile
FROM metabase/metabase:vX.XX.X
```

### 2. Update the Ingestion Image (If Applicable)

Edit `ingestion/Dockerfile.base` or `ingestion/Dockerfile.toggl` to change base images, dependencies, or source code:

```dockerfile
# Base image
FROM python:3.12-slim

# Add any new dependencies
RUN pip install ...
```

If adding a new optional source, update `pyproject.toml`:

```toml
[project.optional-dependencies]
my_source = [
    "my-source-sdk>=1.0",
]
```

Update the Docker build to include the new dependency group:

```dockerfile
RUN pip install .[toggl,my_source]
```

### 3. Push a Release Tag

Push a tag following the date format `YYYY.MM.N` to trigger the deployment:

```bash
git tag -a 2026.11.1
git push origin 2026.11.1
```

The `Deploy` workflow will then:

1. Build and push 3 Docker images to GHCR (see [how it works](../explanation/deployment-production.md#automated-deployment-tag-push))
2. Apply Terraform with the new image tags
3. Roll out the new Metabase revision on Cloud Run
4. Update the ingestion-toggl Cloud Run Job
5. Run a health check against the Metabase service

### 4. Verify the Deployment

After the workflow completes, verify the deployment:

```bash
# Check the Cloud Run revision
gcloud run services describe metabase --project=data-warehouse-492522 \
  --region=us-west1 --format='value(status.url)'

# Verify the running image
gcloud run services describe metabase --project=data-warehouse-492522 \
  --region=us-west1 --format='value(spec.template.spec.containers[0].image)'

# Test the health endpoint
curl -f https://metabase-2xhfhhdfxq-uw.a.run.app/api/health
```

## Rollback Procedure

If a new version has issues, revert the tag and push a new one pointing to the previous version:

1. **Revert the Dockerfile** to the previous Metabase version (or the previous git commit).
2. **Push a new tag** to trigger a fresh deployment:

   ```bash
   git checkout <previous-working-commit>
   git tag -a 2026.11.2
   git push origin 2026.11.2
   ```

### Quick Rollback (Manual Dispatch)

For a faster rollback without pushing a new tag, use `workflow_dispatch`:

```bash
# Trigger from GitHub Actions UI → Actions → Deploy → Run workflow
# Set metabase_image_tag to the previous working SHA or tag
```

### Revert to Previous Cloud Run Revision

If Terraform changes need to be reverted, you can also roll back to a previous Cloud Run revision:

```bash
# List revisions
gcloud run revisions list --service=metabase --project=data-warehouse-492522 --region=us-west1

# Route traffic back to a previous revision
gcloud run services update-traffic metabase --project=data-warehouse-492522 \
  --region=us-west1 --to-revisions=<previous-revision-name>=100
```

## Database Migration Considerations

Metabase may include database migrations with new versions. Be aware of the following:

- Migrations run automatically on startup when the container starts.
- Rolling updates ensure the previous version handles requests while the new version starts.
- If a migration fails, the previous revision can be rolled back quickly.

### Pre-Upgrade Checklist

- [ ] Review the Metabase release notes (https://github.com/metabase/metabase/releases) for any database migration requirements
- [ ] Ensure the Cloud SQL backup is recent and healthy (run a backup manually if needed — see [Cloud SQL Backup Verification](cloud-sql-backup-verification.md))
- [ ] Ensure you can rollback to the previous version

### Post-Upgrade Checklist

- [ ] Verify Cloud Run revision is running the new image
- [ ] Test the `/api/health` endpoint returns `200 OK`
- [ ] Log in as an admin and verify dashboards load correctly
- [ ] Check that scheduled tasks (pulses, alerts) are running
