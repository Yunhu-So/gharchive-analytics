with all_actor_sightings as (
    select actor_id, actor_login, event_created_at, is_bot_actor from {{ ref('stg_gh__pull_request_events') }}
    union all
    select actor_id, actor_login, event_created_at, is_bot_actor from {{ ref('stg_gh__push_events') }}
    union all
    select actor_id, actor_login, event_created_at, is_bot_actor from {{ ref('stg_gh__watch_events') }}
)

select
    actor_id,
    arg_max(actor_login, event_created_at) as actor_login,
    bool_or(is_bot_actor) as is_bot_actor,
    min(event_created_at) as first_seen_at,
    max(event_created_at) as last_seen_at
from all_actor_sightings
group by actor_id
