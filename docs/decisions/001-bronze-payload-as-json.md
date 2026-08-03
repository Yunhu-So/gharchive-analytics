# 001: keep bronze payload as an unparsed JSON string

## Decision

Bronze parquet files store one row per GH Archive event with typed columns for
the fields common to every event (`id`, `type`, `actor`, `repo`, `created_at`, `org`)
and a single `payload` column holding the raw JSON string, unparsed.

Per-event-type unnesting of `payload` happens only in the dbt staging layer,
one model per event type of interest.

## Alternatives rejected

**Unnest payload at ingest time, one bronze table per event type.** Rejected
because payload schemas differ per event type and drift over time (GitHub has
added and changed event fields since 2011 without notice). Unnesting at
ingest time means any new field, renamed field, or new event type forces a
bronze re-ingest across the whole backfill. Ingest should never need to know
about payload shape.

**Store payload as a nested STRUCT/MAP column instead of a string.** Rejected
because DuckDB and BigQuery would both need a schema for the struct at write
time, which reintroduces the same coupling: a payload shape change becomes a
bronze schema migration instead of a downstream model change.

## Consequence

Staging models pay a JSON-parsing cost on every read instead of once at
ingest. Given hourly file sizes and the fact that staging models are views (not
materialized), this cost is acceptable and is the standard bronze/silver
tradeoff.

Measured against the real backfill, that cost is concrete, not theoretical:
`PullRequestEvent` payloads (which embed GitHub's full nested `pull_request`
object) average 15.8 KB and run up to 254 KB. At ~1.17M rows for just that
one event type across the first 40 days of 2015, reading `payload` alone is
tens of GB of raw text — enough to OOM a `dbt build` at DuckDB's default
memory settings, independent of row count, once discovered while validating
the incremental/full-refresh equivalence test. Two things made this
survivable rather than a reason to reconsider the decision:

1. Filtering to `dt` (the hive partition column) before scanning, not just
   `created_at` (a data column parquet can't prune files on) — the actual
   forcing function; see ADR 002.
2. Running DuckDB with a memory limit sized for the payload volume in play
   (`dbt/profiles.yml`'s `settings.memory_limit`, overridable via
   `DUCKDB_MEMORY_LIMIT`), not DuckDB's small default.
