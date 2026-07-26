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
    try_cast(json_extract_string(payload, '$.pull_request.number') as bigint) as pr_number,
    try_cast(json_extract_string(payload, '$.pull_request.id') as bigint) as pr_id,
    try_cast(json_extract_string(payload, '$.comment.created_at') as timestamp) as commented_at,
    json_extract_string(payload, '$.comment.user.login') as commenter_login,
    try_cast(json_extract_string(payload, '$.comment.user.id') as bigint) as commenter_id,
    try_cast(json_extract_string(payload, '$.comment.pull_request_review_id') as bigint)
        as pull_request_review_id,
    {{ is_bot_actor('actor.login') }} as is_bot_actor
from deduped
where
    type = 'PullRequestReviewCommentEvent'
    and created_at >= '{{ var("marts_start_date") }}'
