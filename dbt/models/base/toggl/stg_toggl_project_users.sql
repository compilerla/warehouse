{{ config(materialized='view') }}

WITH external_project_users AS (
    SELECT *
    FROM {{ source('raw_toggl', 'project_users') }}
),

stg_toggl_project_users AS (
    -- Type-cast raw CSV string columns to explicit BigQuery types.

    SELECT
        CAST({{ trim_make_empty_string_null('user_id') }} AS INT64) AS user_id,
        CAST({{ trim_make_empty_string_null('project_id') }} AS INT64) AS project_id,
        {{ trim_make_empty_string_null('role') }} AS role,
        {{ trim_make_empty_string_null('access') }} AS access,
        {{ cast_datetime('created_at') }} AS created_at,
        {{ cast_datetime('updated_at') }} AS updated_at,
        {{ cast_date('pull_date') }} AS pull_date
    FROM external_project_users
)

SELECT * FROM stg_toggl_project_users
