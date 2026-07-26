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
    {{ is_bot_actor('actor.login') }} as is_bot_actor
from deduped
where
    type = 'WatchEvent'
    and created_at >= '{{ var("marts_start_date") }}'
