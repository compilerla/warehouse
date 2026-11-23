{{ config(materialized='view') }}

WITH external_users AS (
    SELECT *
    FROM {{ source('raw_toggl', 'users') }}
),

stg_toggl_users AS (
    -- Type-cast raw CSV string columns to explicit BigQuery types.
    -- Boolean columns use lowercase true/false from Toggl.

    SELECT
        CAST({{ trim_make_empty_string_null('id') }} AS INT64) AS user_id,
        {{ trim_make_empty_string_null('uuid') }} AS uuid,
        {{ trim_make_empty_string_null('name') }} AS name,
        {{ trim_make_empty_string_null('email') }} AS email,
        {{ trim_make_empty_string_null('timezone') }} AS timezone,
        CAST({{ trim_make_empty_string_null('timezone_offset') }} AS INT64) AS timezone_offset,
        CAST({{ trim_make_empty_string_null('default_workspace_id') }} AS INT64) AS default_workspace_id,
        {{ cast_date('start_date') }} AS start_date,
        {{ cast_date('end_date') }} AS end_date,
        {{ parse_boolean('has_photo') }} AS has_photo,
        {{ trim_make_empty_string_null('money') }} AS money,
        {{ cast_datetime('created_at') }} AS created_at,
        {{ cast_datetime('updated_at') }} AS updated_at,
        {{ cast_date('pull_date') }} AS pull_date
    FROM external_users
)

SELECT * FROM stg_toggl_users
