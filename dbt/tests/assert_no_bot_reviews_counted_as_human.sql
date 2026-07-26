-- fails if a PR's first_review_at cannot be attributed to any non-bot
-- responder. A bot event coincidentally sharing the same timestamp as a
-- legitimate human response is not a violation on its own: what matters is
-- that the chosen timestamp is achievable by a human, not that no bot ever
-- touched the PR at that instant. See ADR 005.

with human_review_candidates as (
    select repo_id, pr_number, reviewed_at as responded_at
    from {{ ref('stg_gh__pull_request_review_events') }}
    where not is_bot_actor

    union all

    select repo_id, pr_number, commented_at as responded_at
    from {{ ref('stg_gh__pull_request_review_comment_events') }}
    where not is_bot_actor

    union all

    select repo_id, issue_number as pr_number, commented_at as responded_at
    from {{ ref('stg_gh__issue_comment_events') }}
    where not is_bot_actor and is_pr_comment
)

select f.*
from {{ ref('fct_pr_review_latency') }} as f
where
    f.first_review_at is not null
    and not exists (
        select 1
        from human_review_candidates as h
        where
            h.repo_id = f.repo_id
            and h.pr_number = f.pr_number
            and h.responded_at = f.first_review_at
    )
