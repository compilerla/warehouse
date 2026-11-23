{% macro cast_datetime(col) -%}
{% set c = col | string %}
{% if c.startswith("'") and c.endswith("'") %}
    {% set c = c[1:-1] %}
{% endif %}
CAST(NULLIF(TRIM({{ c }}), '') AS DATETIME)
{%- endmacro %}
