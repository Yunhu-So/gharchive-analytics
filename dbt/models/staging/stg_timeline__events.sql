-- demonstrates the Timeline API adapter pattern (ADR 004) over one month
-- of 2014 data. Deliberately not unioned into any 2015+ model: the id here
-- is synthesized (the Timeline API had none), and actor.id is always null
-- (pre-2015 actors carry no stable numeric id, only a login).

{{ config(tags=['timeline_demo']) }}

select
    id as event_id,
    type,
    actor.login as actor_login,
    repo.id as repo_id,
    repo.name as repo_name,
    created_at as event_created_at,
    payload
from {{ source('bronze_timeline', 'events') }}
