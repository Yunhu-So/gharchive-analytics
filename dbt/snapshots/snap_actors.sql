{% snapshot snap_actors %}

{{
    config(
        target_schema='snapshots',
        unique_key='actor_id',
        strategy='check',
        check_cols=['actor_login'],
    )
}}

    select actor_id, actor_login
    from {{ ref('dim_actor') }}

{% endsnapshot %}
