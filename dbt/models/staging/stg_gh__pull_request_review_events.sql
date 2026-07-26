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
    json_extract_string(payload, '$.review.state') as review_state,
    try_cast(json_extract_string(payload, '$.review.submitted_at') as timestamp) as reviewed_at,
    json_extract_string(payload, '$.review.user.login') as reviewer_login,
    try_cast(json_extract_string(payload, '$.review.user.id') as bigint) as reviewer_id,
    {{ is_bot_actor('actor.login') }} as is_bot_actor
from deduped
where
    type = 'PullRequestReviewEvent'
    and created_at >= '{{ var("marts_start_date") }}'
