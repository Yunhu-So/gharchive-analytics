# Architecture

```mermaid
flowchart TD
    A[data.gharchive.org hourly .json.gz] --> B[Airflow: gharchive_ingest DAG]
    B -->|dynamic task mapping, 24 hours per day| C[bronze parquet\ndt=YYYY-MM-DD/hour=HH]
    C -->|Airflow Asset emitted| D[Airflow: gharchive_transform DAG\nastronomer-cosmos]
    D --> E[dbt staging\none model per event type]
    E --> I[dbt intermediate\nint_review_candidates]
    I --> G[dbt intermediate\nint_pr_lifecycle]
    E --> G
    E --> J[dbt marts\ndim_repo, dim_actor, dim_date]
    G --> H[dbt marts\nfct_pr_review_latency\nfct_repo_daily_activity\nfct_contributor_cohorts]
    J -->|snapshotted each run| F[dbt snapshots\nsnap_repos, snap_actors]
```

## Ingestion (bronze)

`gharchive_ingest` is a daily DAG (`@daily`, `catchup=True`) that dynamically
maps 24 tasks, one per hour of the logical date, rather than scheduling
hourly. A daily DAG produces about 365 DAG runs a year; an hourly DAG would
produce about 8,760. Airflow's scheduler and metadata database overhead scale
with DAG run count more than with task count within a run, so daily-with-24-
mapped-tasks is cheaper to operate at backfill scale without changing what
gets processed.

Each mapped task downloads one hour, validates the gzip is not truncated,
and writes to a hive-partitioned parquet path (`bronze/dt=.../hour=.../`) via
write-to-temp-then-atomic-rename, so a crashed or retried task never leaves a
partially written partition visible to readers. This is what makes
re-running a historical date safe: readers either see the old partition or
the fully-written new one, never a partial one.

A `gharchive_download_pool` Airflow pool caps concurrent hour downloads at 8
regardless of how many DAG runs are active simultaneously, so a large
backfill does not turn into a burst of concurrent requests against a public,
rate-limit-sensitive source.

404 responses are terminal and expected: some hours in 2011-2012 are genuinely
missing from the archive. These are recorded in a `missing_hours` control
table with a `reason` column and the task succeeds. Everything else that can
go wrong (timeout, 5xx, truncated gzip) is retried with exponential backoff
and only recorded as `missing_hours` if retries are exhausted with a non-404
reason, distinguishing "this hour will never exist" from "this attempt
failed."

Bronze keeps `payload` as an unparsed JSON string ([ADR 001](docs/decisions/001-bronze-payload-as-json.md)).
Only the columns shared by every event (`id`, `type`, `actor`, `repo`, `org`,
`created_at`) are typed at ingest time.

## Staging (silver)

One dbt model per event type of interest, each responsible for unnesting its
own `payload` shape and deduplicating on event `id`
([ADR 002](docs/decisions/002-dedupe-strategy.md)). Staging models are views:
they are cheap to keep in sync with bronze and do not require a separate
materialization step to pick up newly landed partitions.

## Intermediate

`int_pr_lifecycle` carries the spine metric's hard part: a PR opened in one
partition can receive its first review in a much later one. See
[ADR 003](docs/decisions/003-incremental-lookback.md) for the lookback window
design.

`int_review_candidates` (the union of formal reviews, review-line comments,
and PR-conversation comments that `int_pr_lifecycle` joins against) is its
own incremental model rather than a CTE, because DuckDB's planner blows past
any memory limit on that specific join shape when it isn't. See the
addendum in ADR 003 for the full story, and the addendum below it for a
second real bug: a non-deterministic tiebreak in `int_pr_lifecycle`'s
first-PR ranking that a row-for-row parity test caught only once run
against the real backfill, not the CI fixture.

## Marts (gold)

`fct_pr_review_latency` is the spine metric, sliced by repo and year.
`dim_repo` and `dim_actor` are built directly from staging with
`arg_max(name, event_created_at)`, giving each repo/actor's most recently
observed name -- every mart that needs an identity joins on the stable
numeric id (never on name), so a rename never silently misattributes
history to begin with. `dim_date` is a plain calendar spine. Secondary
marts (`fct_repo_daily_activity`, `fct_contributor_cohorts`) are derived
from the same staging/intermediate layer and exist only because they are
cheap once the spine is built, not because they were independently planned.

## Snapshots

`snap_repos` and `snap_actors` snapshot `dim_repo` and `dim_actor`
(strategy `check` on `repo_name`/`actor_login`), giving an SCD2 audit trail
of every observed rename over successive runs -- when a repo transferred
orgs or an actor changed their login, and what the value was before. Kept
downstream of the dims rather than duplicating the same
"most recent name per id" logic a second time, and separate from the
correctness property described above: the snapshots are a historical
record for anyone asking "what did this repo used to be called," not a
dependency anything else in the DAG needs to stay correct.

## Targets

DuckDB is the only target where incremental logic is developed and tested;
it has no restrictions on DML. BigQuery is treated as a second target that
the same dbt project can compile against, constrained by the BigQuery
Sandbox's lack of DML support (see the BigQuery section of the README).
