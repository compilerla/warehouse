{{ config(materialized='table') }}

WITH base AS (
    SELECT *
    FROM {{ ref('stg_toggl_timesheets') }}
),

time_entry_summary AS (
    -- Aggregate time-sheet records at the project level.
    -- Each row represents one time-entry record with its associated project.

    SELECT
        time_entry_id,
        date,
        project_id,
        project_name,
        client_id,
        client_name,
        user_id,
        SUM(duration_seconds) AS total_duration_seconds,
        MIN(pull_date) AS earliest_pull_date,
        MAX(pull_date) AS latest_pull_date
    FROM base
    WHERE time_entry_id IS NOT NULL
    GROUP BY
        time_entry_id,
        date,
        project_id,
        project_name,
        client_id,
        client_name,
        user_id
)

SELECT * FROM time_entry_summary
