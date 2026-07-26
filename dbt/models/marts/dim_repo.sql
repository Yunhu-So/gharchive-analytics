with all_repo_sightings as (
    select repo_id, repo_name, event_created_at from {{ ref('stg_gh__pull_request_events') }}
    union all
    select repo_id, repo_name, event_created_at from {{ ref('stg_gh__push_events') }}
    union all
    select repo_id, repo_name, event_created_at from {{ ref('stg_gh__watch_events') }}
)

select
    repo_id,
    arg_max(repo_name, event_created_at) as repo_name,
    min(event_created_at) as first_seen_at,
    max(event_created_at) as last_seen_at
from all_repo_sightings
group by repo_id
