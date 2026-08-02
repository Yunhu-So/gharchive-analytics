# 006: partition marts on date, cluster on repo_id

## Decision

On the `prod` (BigQuery) target, the two marts with a meaningful row count
(`fct_pr_review_latency`, `fct_repo_daily_activity`) are date-partitioned
and clustered on `repo_id`:

- `fct_pr_review_latency`: partitioned on `opened_at` (day granularity),
  clustered on `repo_id`
- `fct_repo_daily_activity`: partitioned on `activity_date` (day
  granularity), clustered on `repo_id`

Both configs are conditional on `target.type == 'bigquery'`; DuckDB gets
`none` for both, since DuckDB has no equivalent concept and dbt-duckdb
ignores the config either way.

Dimension tables (`dim_repo`, `dim_actor`, `dim_date`) are not partitioned:
they are small (one row per repo/actor/day) and every query against them is
effectively a full scan regardless of partitioning.

## Alternatives rejected

**Partition on `opened_year` instead of `opened_at`.** Rejected: BigQuery's
date/timestamp partitioning is native and query planners prune on it
directly; partitioning on an integer year column would require an
`_PARTITIONTIME`-style workaround or an integer-range partition, which is
more configuration for the same result given every query in this project
already filters or groups by a real date/timestamp column.

**Cluster on `pr_author_id` instead of `repo_id`.** Rejected. The spine
metric and every mart in this project group and filter by repository first
(review latency by repo and year, activity by repo and day); clustering on
`repo_id` matches the actual query shape. Author-level analysis is a
secondary axis, not the primary one.

**No clustering, partitioning only.** Rejected once it was clear that most
realistic queries filter to a handful of repos within a date range — cluster
pruning on `repo_id` is what turns "scan this partition" into "scan this
partition for these repos," which is the difference this ADR's own
before/after measurement is meant to demonstrate.

## Consequence

Measuring bytes scanned before and after this configuration requires
running the actual mart-building queries against a real BigQuery project;
that measurement has not been taken yet (no GCP project has been
provisioned against `terraform/`, per the project's phased scope) and is a
known gap the README's status section calls out rather than fabricating.
