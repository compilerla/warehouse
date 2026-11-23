{{ config(materialized='view') }}

WITH external_clients AS (
    SELECT *
    FROM {{ source('raw_toggl', 'clients') }}
),

stg_toggl_clients AS (
    -- Type-cast raw CSV string columns to explicit BigQuery types.

    SELECT
        CAST({{ trim_make_empty_string_null('id') }} AS INT64) AS client_id,
        {{ trim_make_empty_string_null('name') }} AS name,
        {{ trim_make_empty_string_null('notes') }} AS notes,
        {{ trim_make_empty_string_null('currency') }} AS currency,
        {{ trim_make_empty_string_null('organization_id') }} AS organization_id,
        {{ cast_datetime('created_at') }} AS created_at,
        {{ cast_datetime('updated_at') }} AS updated_at,
        {{ cast_date('pull_date') }} AS pull_date
    FROM external_clients
)

SELECT * FROM stg_toggl_clients
