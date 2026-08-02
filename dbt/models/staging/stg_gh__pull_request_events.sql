-- filter to this event type before deduping, not after: row_number() over
-- the full bronze source (every event type) is what actually blew up
-- memory at scale, since the type filter was only applied in the outer
-- query, after the window function had already scanned everything.
with base as (
    select *
    from {{ source('bronze', 'events') }}
    where
        type = 'PullRequestEvent'
        and created_at >= '{{ var("marts_start_date") }}'
        -- filters on the dt hive partition column, not just created_at:
        -- created_at alone can't prune parquet files (it's a data column,
        -- not the partition column), so DuckDB would open every partition
        -- ever ingested to evaluate it. dt >= the same cutoff, evaluated
        -- against the partition path itself, is what actually skips them.
        and dt >= cast('{{ var("marts_start_date") }}' as date)
),

deduped as (
    {{ dedupe_events("base") }}
)

select
    id as event_id,
    created_at as event_created_at,
    actor.id as actor_id,
    actor.login as actor_login,
    repo.id as repo_id,
    repo.name as repo_name,
    json_extract_string(payload, '$.action') as action,
    try_cast(json_extract_string(payload, '$.number') as bigint) as pr_number,
    try_cast(json_extract_string(payload, '$.pull_request.id') as bigint) as pr_id,
    json_extract_string(payload, '$.pull_request.user.login') as pr_author_login,
    try_cast(json_extract_string(payload, '$.pull_request.user.id') as bigint) as pr_author_id,
    try_cast(json_extract_string(payload, '$.pull_request.created_at') as timestamp) as pr_created_at,
    try_cast(json_extract_string(payload, '$.pull_request.closed_at') as timestamp) as pr_closed_at,
    try_cast(json_extract_string(payload, '$.pull_request.merged_at') as timestamp) as pr_merged_at,
    json_extract_string(payload, '$.pull_request.state') as pr_state,
    {{ is_bot_actor('actor.login') }} as is_bot_actor,
    {{ is_bot_actor("json_extract_string(payload, '$.pull_request.user.login')") }} as is_bot_pr_author
from deduped
