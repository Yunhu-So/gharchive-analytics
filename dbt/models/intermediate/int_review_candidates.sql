{{
    config(
        materialized='table' if (target.type == 'bigquery' and not var('bq_allow_dml', false)) else 'incremental',
        incremental_strategy='insert_overwrite' if target.type == 'bigquery' else 'append',
        partition_by={'field': 'responded_at', 'data_type': 'timestamp', 'granularity': 'day'} if target.type == 'bigquery' else none,
    )
}}

-- section 7.1: first review/comment can be a formal review, a line-level
-- review comment, or a plain PR conversation comment (IssueCommentEvent
-- where the issue is actually a pull request).
--
-- This is its own model, not a CTE inside int_pr_lifecycle: DuckDB's
-- optimizer, when this union of three windowed staging views feeds
-- straight into int_pr_lifecycle's inequality-predicate join, blows past
-- multi-GB memory limits in under a second regardless of how much memory
-- is given to it -- reproduced down to a single day of data, and confirmed
-- fixed purely by materializing the union into a real table before that
-- join runs (no row-count or logic change). Review/comment events are
-- immutable once captured, so a plain append incremental is correct here:
-- unlike int_pr_lifecycle's own reopen handling, nothing about an already-
-- captured review or comment ever needs reprocessing.
select repo_id, pr_number, reviewer_id as responder_id, reviewed_at as responded_at
from {{ ref('stg_gh__pull_request_review_events') }}
where
    not is_bot_actor
    and reviewer_id is not null
{% if is_incremental() %}
    and reviewed_at > (select coalesce(max(responded_at), '1970-01-01'::timestamp) from {{ this }})
    {% endif %}

union all

select repo_id, pr_number, commenter_id as responder_id, commented_at as responded_at
from {{ ref('stg_gh__pull_request_review_comment_events') }}
where
    not is_bot_actor
    and commenter_id is not null
{% if is_incremental() %}
    and commented_at > (select coalesce(max(responded_at), '1970-01-01'::timestamp) from {{ this }})
    {% endif %}

union all

select repo_id, issue_number as pr_number, commenter_id as responder_id, commented_at as responded_at
from {{ ref('stg_gh__issue_comment_events') }}
where
    not is_bot_actor
    and is_pr_comment
    and commenter_id is not null
{% if is_incremental() %}
    and commented_at > (select coalesce(max(responded_at), '1970-01-01'::timestamp) from {{ this }})
    {% endif %}
