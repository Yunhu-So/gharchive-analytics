{% snapshot snap_repos %}

{{
    config(
        target_schema='snapshots',
        unique_key='repo_id',
        strategy='check',
        check_cols=['repo_name'],
    )
}}

    select repo_id, repo_name
    from {{ ref('dim_repo') }}

{% endsnapshot %}
