-- fails if any row in int_pr_lifecycle isn't actually its author's earliest
-- PR in that repo. Guards the (pr_created_at, pr_number) tiebreak in
-- int_pr_lifecycle's all_pr_opens window function: GitHub's event
-- timestamps only resolve to the second, so two PRs by the same author in
-- the same repo can genuinely tie on pr_created_at (observed for real in
-- the backfill -- a repo opening PRs #4 and #5 by the same author in the
-- same second). Without a deterministic, semantically-correct tiebreak,
-- row_number() can pick either as "first," and a full-refresh run can pick
-- a different one than an incremental run of the same logical query.
-- pr_number is assigned by GitHub in true creation order, so it's the
-- right tiebreak, not just a deterministic one.

with candidate_opens as (
    select repo_id, pr_number, pr_author_id, pr_created_at
    from {{ ref('stg_gh__pull_request_events') }}
    where
        action = 'opened'
        and pr_author_id is not null
        and not is_bot_pr_author
)

select l.repo_id, l.pr_number, l.pr_author_id, l.opened_at, c.pr_number as earlier_pr_number
from {{ ref('int_pr_lifecycle') }} as l
inner join candidate_opens as c
    on l.repo_id = c.repo_id and l.pr_author_id = c.pr_author_id
where
    c.pr_created_at < l.opened_at
    or (c.pr_created_at = l.opened_at and c.pr_number < l.pr_number)
