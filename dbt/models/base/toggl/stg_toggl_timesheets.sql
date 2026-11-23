{{ config(materialized='view') }}

WITH external_timesheets AS (
    SELECT *
    FROM {{ source('raw_toggl', 'timesheets') }}
),

stg_toggl_timesheets AS (
    -- Type-cast raw CSV string columns to explicit BigQuery types.
    -- Duration is in milliseconds from the Toggl API; convert to seconds (/1000).
    -- Boolean columns use lowercase true/false from Toggl.

    SELECT
        {{ trim_make_empty_string_null('time_entry_id') }} AS time_entry_id,
        {{ cast_date('date') }} AS date,
        {{ trim_make_empty_string_null('start_time') }} AS start_time,
        {{ trim_make_empty_string_null('end_time') }} AS end_time,
        {{ trim_make_empty_string_null('user_id') }} AS user_id,
        {{ trim_make_empty_string_null('client_id') }} AS client_id,
        {{ trim_make_empty_string_null('client_name') }} AS client_name,
        {{ trim_make_empty_string_null('project_id') }} AS project_id,
        {{ trim_make_empty_string_null('project_name') }} AS project_name,
        {{ trim_make_empty_string_null('task_id') }} AS task_id,
        {{ trim_make_empty_string_null('task_name') }} AS task_name,
        {{ parse_boolean('billable') }} AS billable,
        CAST(NULLIF(TRIM({{ trim_make_empty_string_null('billable_rate') }}), '') AS FLOAT64) AS billable_rate,
        {{ trim_make_empty_string_null('description') }} AS description,
        CAST(NULLIF(TRIM({{ trim_make_empty_string_null('duration') }}), '') AS INT64) / 1000 AS duration_seconds,
        {{ parse_boolean('project_is_private') }} AS project_is_private,
        {{ trim_make_empty_string_null('project_status') }} AS project_status,
        {{ trim_make_empty_string_null('client_status') }} AS client_status,
        {{ trim_make_empty_string_null('tags') }} AS tags,
        {{ cast_date('pull_date') }} AS pull_date
    FROM external_timesheets
)

SELECT * FROM stg_toggl_timesheets
