with deduped as (
    {{ dedupe_events(source('bronze', 'events')) }}
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
where
    type = 'IssueCommentEvent'
    and created_at >= '{{ var("marts_start_date") }}'
