{{
    config(
        materialized='table' if (target.type == 'bigquery' and not var('bq_allow_dml', false)) else 'incremental',
        unique_key=['repo_id', 'pr_number'],
        incremental_strategy='insert_overwrite' if target.type == 'bigquery' else 'delete+insert',
        partition_by={'field': 'opened_at', 'data_type': 'timestamp', 'granularity': 'day'} if target.type == 'bigquery' else none,
    )
}}

{#-
    section 7.5's uncertainty cutoff only needs the single earliest
    event_created_at value ever seen. Computed once here via run_query
    (a compile-time roundtrip) rather than as a `data_start` CTE in the
    query below: on duckdb, adding that CTE back -- even as a plain
    aggregate with no window function of its own, cross joined instead of
    correlated -- reproduces the same multi-GB-regardless-of-limit OOM as
    int_review_candidates did (see that model's note); this whole query
    shape is fragile to any extra CTE that touches the staging views a
    second time. A single scalar known before the query runs sidesteps it
    rather than chasing yet another materialization workaround.

    Guarded on the source relation actually existing: sqlfluff (and plain
    `dbt compile`) render this model without ever running the DAG, so the
    staging view this queries hasn't been created yet in that context.
    Falling back to a placeholder there is fine -- lint only checks that
    the rendered SQL is syntactically valid, not this literal's value.
-#}
{% set stg_pr_events = ref('stg_gh__pull_request_events') %}
{% set stg_pr_events_relation = (
    adapter.get_relation(stg_pr_events.database, stg_pr_events.schema, stg_pr_events.identifier)
    if execute else none
) %}
{% if stg_pr_events_relation %}
    {% set min_created_at_query %}
        select min(event_created_at) as min_created_at from {{ stg_pr_events }}
    {% endset %}
    {% set min_created_at = run_query(min_created_at_query).columns[0].values()[0] %}
{% else %}
    {% set min_created_at = '1970-01-01' %}
{% endif %}

with all_pr_opens as (
    select
        repo_id,
        pr_number,
        pr_author_id,
        pr_author_login,
        pr_created_at,
        pr_closed_at,
        pr_merged_at,
        row_number() over (
            partition by repo_id, pr_author_id
            order by pr_created_at
        ) as author_repo_pr_seq
    from {{ ref('stg_gh__pull_request_events') }}
    where
        action = 'opened'
        and pr_author_id is not null
        -- a bot opening a PR is not a "contributor" the spine metric counts; ADR 005
        and not is_bot_pr_author
),

-- first-time-contributor status needs each author's full history on the repo,
-- so this scan is never bounded by the incremental window; only the review
-- join below is bounded, which is where the actual cost lives.
first_time_pr_opens as (
    select
        repo_id,
        pr_number,
        pr_author_id,
        pr_author_login,
        pr_created_at,
        pr_closed_at,
        pr_merged_at,
        true as is_first_time_contributor
    from all_pr_opens
    where author_repo_pr_seq = 1
    {% if is_incremental() %}
        and (
            pr_created_at > (select coalesce(max(opened_at), '1970-01-01'::timestamp) from {{ this }})
            or (repo_id, pr_number) in (
                select repo_id, pr_number
                from {{ this }}
                where
                    first_review_at is null
                    and opened_at >= current_timestamp - interval '{{ var("pr_lifecycle_max_age_days") }}' day
            )
        )
    {% endif %}
),

-- section 7.1: first review/comment can be a formal review, a line-level
-- review comment, or a plain PR conversation comment. Sourced from
-- int_review_candidates (its own model, not a CTE here) because DuckDB's
-- optimizer blows past multi-GB memory limits in under a second when that
-- union of three windowed staging views feeds straight into the
-- inequality-predicate join below; materializing it as a real table first
-- is what fixes it. See int_review_candidates.sql for the full note.
review_candidates as (
    select repo_id, pr_number, responder_id, responded_at
    from {{ ref('int_review_candidates') }}
    {% if is_incremental() %}
        where responded_at >= current_timestamp
            - interval '{{ var("pr_lifecycle_max_age_days") + var("pr_lifecycle_lookback_days") }}' day
    {% endif %}
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
)

select
    o.repo_id,
    o.pr_number,
    o.pr_author_id,
    o.pr_author_login,
    o.pr_created_at as opened_at,
    o.pr_closed_at as closed_at,
    o.pr_merged_at as merged_at,
    fr.first_review_at,
    o.is_first_time_contributor,
    date_diff('second', o.pr_created_at, fr.first_review_at) as review_latency_seconds,
    extract(year from o.pr_created_at) as opened_year,
    -- section 7.5: an actor whose first observed PR-open falls within the
    -- uncertainty window of the earliest data we have could have opened
    -- prior PRs before the backfill started; we have no way to know.
    o.pr_created_at <= timestamp '{{ min_created_at }}'
    + interval '{{ var("first_contributor_uncertainty_days") }}' day
        as is_first_contributor_uncertain
from first_time_pr_opens as o
left join first_response as fr
    on
        o.repo_id = fr.repo_id
        and o.pr_number = fr.pr_number
