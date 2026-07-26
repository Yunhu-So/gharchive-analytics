-- fails if any PR's first_review_at is earlier than when it was opened.
-- Required by ADR 003 even before int_pr_lifecycle exists, since
-- fct_pr_review_latency computes the same invariant in phase 2.

select *
from {{ ref('fct_pr_review_latency') }}
where
    first_review_at is not null
    and first_review_at < opened_at
