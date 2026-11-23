{% macro parse_boolean(col) -%}
{% set c = col | string %}
{% if c.startswith("'") and c.endswith("'") %}
    {% set c = c[1:-1] %}
{% endif %}
CASE
    WHEN {{ c }} IS NULL THEN NULL
    WHEN TRIM(UPPER({{ c }})) IN ('TRUE', '1', 'YES', 'Y', 'T') THEN TRUE
    WHEN TRIM(UPPER({{ c }})) IN ('FALSE', '0', 'NO', 'N', 'F') THEN FALSE
    ELSE NULL
END
{%- endmacro %}
