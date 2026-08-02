-- the spine metric. All lifecycle/lookback logic lives in int_pr_lifecycle
-- (ADR 003); this mart is a thin, stable-grain projection over it.

{{
    config(
        partition_by={'field': 'opened_at', 'data_type': 'timestamp', 'granularity': 'day'}
        if target.type == 'bigquery' else none,
        cluster_by=['repo_id'] if target.type == 'bigquery' else none,
    )
}}

select
    repo_id,
    pr_number,
    pr_author_id,
    pr_author_login,
    opened_at,
    first_review_at,
    review_latency_seconds,
    opened_year,
    is_first_time_contributor,
    is_first_contributor_uncertain
from {{ ref('int_pr_lifecycle') }}
