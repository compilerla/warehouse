{{ config(materialized='table') }}

WITH base AS (
    SELECT *
    FROM {{ ref('stg_toggl_timesheets') }}
),

weekly_summary AS (
    -- Aggregate by project and calendar week.
    -- date is already DATE-typed from the staging layer.

    SELECT
        project_id,
        project_name,
        client_id,
        client_name,
        COALESCE(
            DATE_TRUNC(date, WEEK(MONDAY)),
            date
        ) AS week_start,
        MAX(date) AS week_end,
        COUNT(*) AS time_entry_count,
        COUNT(DISTINCT user_id) AS user_count
    FROM base
    WHERE time_entry_id IS NOT NULL
    GROUP BY
        project_id,
        project_name,
        client_id,
        client_name,
        DATE_TRUNC(date, WEEK(MONDAY))
)

SELECT * FROM weekly_summary
