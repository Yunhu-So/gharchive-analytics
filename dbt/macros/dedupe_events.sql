{% macro dedupe_events(relation, id_column='id', order_column='created_at') %}
    select *
    from (
        select
            *,
            row_number() over (
                partition by {{ id_column }}
                order by {{ order_column }}
            ) as _dedupe_rn
        from {{ relation }}
    )
    where _dedupe_rn = 1
{% endmacro %}
