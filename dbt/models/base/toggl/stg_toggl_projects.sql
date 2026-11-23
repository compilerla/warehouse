{{ config(materialized='view') }}

WITH external_projects AS (
    SELECT *
    FROM {{ source('raw_toggl', 'projects') }}
),

stg_toggl_projects AS (
    -- Type-cast raw CSV string columns to explicit BigQuery types.
    -- Boolean columns use lowercase true/false from Toggl.

    SELECT
        CAST({{ trim_make_empty_string_null('id') }} AS INT64) AS project_id,
        {{ trim_make_empty_string_null('name') }} AS name,
        {{ trim_make_empty_string_null('color') }} AS color,
        {{ parse_boolean('is_private') }} AS is_private,
        {{ trim_make_empty_string_null('status') }} AS status,
        {{ trim_make_empty_string_null('client_id') }} AS client_id,
        {{ trim_make_empty_string_null('client_name') }} AS client_name,
        {{ trim_make_empty_string_null('organization_id') }} AS organization_id,
        {{ cast_datetime('created_at') }} AS created_at,
        {{ cast_datetime('updated_at') }} AS updated_at,
        {{ parse_boolean('billable') }} AS billable,
        {{ cast_date('pull_date') }} AS pull_date
    FROM external_projects
)

SELECT * FROM stg_toggl_projects
