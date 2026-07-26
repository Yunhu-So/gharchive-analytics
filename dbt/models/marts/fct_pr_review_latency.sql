-- phase 2: full-refresh version. Phase 3 moves this logic into an incremental
-- int_pr_lifecycle model with a lookback window (see ADR 003); this model
-- will then become a thin select from it.

with pr_opens as (
    select
        repo_id,
        pr_number,
        pr_author_id,
        pr_author_login,
        pr_created_at,
        row_number() over (
            partition by repo_id, pr_author_id
            order by pr_created_at
        ) as author_repo_pr_seq
    from {{ ref('stg_gh__pull_request_events') }}
    where
        action = 'opened'
        and pr_author_id is not null
        -- a bot opening a PR (dependabot, github-actions, ...) is not a
        -- "contributor" the spine metric cares about; see ADR 005.
        and not is_bot_pr_author
),

first_time_pr_opens as (
    select
        repo_id,
        pr_number,
        pr_author_id,
        pr_author_login,
        pr_created_at,
        true as is_first_time_contributor
    from pr_opens
    where author_repo_pr_seq = 1
),

-- section 7.1: first review/comment can be a formal review, a line-level
-- review comment, or a plain PR conversation comment (IssueCommentEvent
-- where the issue is actually a pull request).
review_candidates as (
    select repo_id, pr_number, reviewer_id as responder_id, reviewed_at as responded_at
    from {{ ref('stg_gh__pull_request_review_events') }}
    where not is_bot_actor and reviewer_id is not null

    union all

    select repo_id, pr_number, commenter_id as responder_id, commented_at as responded_at
    from {{ ref('stg_gh__pull_request_review_comment_events') }}
    where not is_bot_actor and commenter_id is not null

    union all

    select repo_id, issue_number as pr_number, commenter_id as responder_id, commented_at as responded_at
    from {{ ref('stg_gh__issue_comment_events') }}
    where not is_bot_actor and is_pr_comment and commenter_id is not null
),

first_response as (
    select
        o.repo_id,
        o.pr_number,
        min(r.responded_at) as first_review_at
    from first_time_pr_opens as o
    inner join review_candidates as r
        on
            o.repo_id = r.repo_id
            and o.pr_number = r.pr_number
            and r.responder_id != o.pr_author_id
            and r.responded_at >= o.pr_created_at
    group by 1, 2
),

data_start as (
    select min(event_created_at) as min_created_at
    from {{ ref('stg_gh__pull_request_events') }}
)

select
    o.repo_id,
    o.pr_number,
    o.pr_author_id,
    o.pr_author_login,
    o.pr_created_at as opened_at,
    fr.first_review_at,
    o.is_first_time_contributor,
    date_diff('second', o.pr_created_at, fr.first_review_at) as review_latency_seconds,
    extract(year from o.pr_created_at) as opened_year,
    -- section 7.5: an actor whose first observed PR-open falls within the
    -- uncertainty window of the earliest data we have could have opened
    -- prior PRs before the backfill started; we have no way to know.
    o.pr_created_at <= (select data_start.min_created_at from data_start)
    + interval '{{ var("first_contributor_uncertainty_days") }}' day
        as is_first_contributor_uncertain
from first_time_pr_opens as o
left join first_response as fr
    on
        o.repo_id = fr.repo_id
        and o.pr_number = fr.pr_number
