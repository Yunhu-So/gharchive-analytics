-- filter to this event type before deduping, not after (see ADR 002 /
-- stg_gh__pull_request_events.sql comment: row_number() over the full
-- bronze source is what actually blows up memory at scale).
with base as (
    select *
    from {{ source('bronze', 'events') }}
    where
        type = 'IssueCommentEvent'
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
    try_cast(json_extract_string(payload, '$.issue.number') as bigint) as issue_number,
    -- per section 7.1: a plain issue comment and a PR conversation comment are
    -- both IssueCommentEvent. issue.pull_request is only present when the
    -- issue this comment belongs to is actually a pull request.
    json_extract_string(payload, '$.issue.pull_request.url') is not null as is_pr_comment,
    try_cast(json_extract_string(payload, '$.comment.created_at') as timestamp) as commented_at,
    json_extract_string(payload, '$.comment.user.login') as commenter_login,
    try_cast(json_extract_string(payload, '$.comment.user.id') as bigint) as commenter_id,
    {{ is_bot_actor('actor.login') }} as is_bot_actor
from deduped
