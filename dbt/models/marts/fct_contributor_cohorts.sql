with pr_opens as (
    select
        repo_id,
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
        and not is_bot_pr_author
)

select
    repo_id,
    pr_author_id,
    -- an actor can rename between PRs, so pr_author_login must not be part
    -- of the grouping key: that would silently split one contributor's
    -- history into two rows. Use the most recent observed login instead.
    arg_max(pr_author_login, pr_created_at) as pr_author_login,
    min(pr_created_at) as first_contribution_at,
    date_trunc('month', min(pr_created_at)) as cohort_month,
    count(*) as total_prs_opened
from pr_opens
group by 1, 2
