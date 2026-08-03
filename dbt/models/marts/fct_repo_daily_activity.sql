{{
    config(
        partition_by={'field': 'activity_date', 'data_type': 'date', 'granularity': 'day'}
        if target.type == 'bigquery' else none,
        cluster_by=['repo_id'] if target.type == 'bigquery' else none,
    )
}}

with daily_events as (
    select repo_id, cast(event_created_at as date) as activity_date, 'push' as event_kind
    from {{ ref('stg_gh__push_events') }}
    where not is_bot_actor

    union all

    select repo_id, cast(event_created_at as date) as activity_date, 'pr_opened' as event_kind
    from {{ ref('stg_gh__pull_request_events') }}
    where action = 'opened' and not is_bot_pr_author

    union all

    select repo_id, cast(event_created_at as date) as activity_date, 'watch' as event_kind
    from {{ ref('stg_gh__watch_events') }}
    where not is_bot_actor
)

select
    repo_id,
    activity_date,
    count(*) filter (where event_kind = 'push') as push_count,
    count(*) filter (where event_kind = 'pr_opened') as pr_opened_count,
    count(*) filter (where event_kind = 'watch') as watch_count
from daily_events
group by 1, 2
