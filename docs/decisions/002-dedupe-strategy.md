# 002: dedupe events on id at the staging layer

## Decision

Every staging model deduplicates on the GH Archive event `id` using
`qualify row_number() over (partition by id order by created_at) = 1`
(or the dbt-duckdb/BigQuery equivalent). A `dbt_utils.unique_combination_of_columns`
test on `id` is attached to every staging model.

## Alternatives rejected

**Dedupe at ingest time by tracking seen ids.** Rejected. It requires the
ingest DAG to hold state across runs (a seen-id index) and turns a stateless,
horizontally-mappable download task into a stateful one. It also does not
compose with idempotent re-ingestion: re-running an hour must always produce
the same bronze output regardless of what other hours have already run.

**Ignore duplicates and rely on downstream aggregation being duplicate-tolerant.**
Rejected. GH Archive hourly files overlap at hour boundaries: the crawler that
produces a given hour's file can pick up events that also land in the
adjacent hour's file. Left undeduplicated, this double-counts events in any
volume-based mart and can attach the same review event to a PR lifecycle
calculation twice. This is exactly the gap between an ingest pipeline that is
nominally idempotent (same bytes in bronze on re-run) and one that is
genuinely idempotent (same row counts and metric values downstream,
regardless of which hour files happen to overlap).

## Consequence

Dedup happens once per staging model rather than once globally, so the same
`row_number()` filter is duplicated across staging models. This is
deliberate: staging models should not depend on each other, and the dedupe
logic is cheap and mechanical enough that a shared macro (`dedupe_events`)
in `dbt/macros/` is used instead of a shared model dependency.
