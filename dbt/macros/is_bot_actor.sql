{% macro is_bot_actor(login_column) %}
    (
        {{ login_column }} ilike '%[bot]'
        or lower(regexp_replace({{ login_column }}, '\[bot\]$', ''))
            in (select lower(login) from {{ ref('known_bot_actors') }})
    )
{% endmacro %}
