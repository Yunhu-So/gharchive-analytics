# 000: data reconnaissance findings

Sample fetched: `https://data.gharchive.org/2024-01-15-9.json.gz` (2024-01-15, hour 9 UTC).

## URL format

Confirmed against a live fetch: the hour segment is **not** zero-padded.

- `.../2024-01-15-9.json.gz` returns `200`.
- `.../2024-01-15-09.json.gz` returns `404`.

The ingest DAG builds URLs as `f"{base}/{dt}-{hour}.json.gz"` with `hour` as a
plain int, never zero-padded. This matches the brief and required no
correction.

## File shape

The file is newline-delimited JSON, one object per line, not a JSON array.
`read_json(..., format='newline_delimited', union_by_name=true)` is required;
`union_by_name` is necessary because different event types in the same file
have structurally different `payload` shapes, and DuckDB needs to union
those shapes across rows within one file.

## Correction to the brief: struct-to-varchar does not produce JSON

The original ingest design cast `payload::varchar` to get a raw JSON string
for bronze. This is wrong: DuckDB's JSON auto-detection infers `payload` as a
nested `STRUCT`, and casting a `STRUCT` to `VARCHAR` produces DuckDB's own
struct-literal text representation (`{key: value, ...}`), not valid JSON.
Downstream `json_extract` / `json.loads()` calls against that text would
fail or silently misparse.

The fix: use `to_json(payload)` instead of `payload::varchar`. `to_json`
(from DuckDB's json extension) serializes the inferred struct back to actual
JSON text. This is what `dags/gharchive_ingest.py` now does. ADR 001's
premise (bronze payload stays an opaque JSON string, decoupled from
per-type schema drift) still holds: the struct inference during the read is
an internal detail of that one file's processing, not something written to
disk or relied on across hours.

## Event types present (this hour, 246,225 events)

| type | count |
|---|---|
| PushEvent | 151,994 |
| CreateEvent | 25,518 |
| PullRequestEvent | 17,336 |
| WatchEvent | 11,632 |
| IssueCommentEvent | 11,118 |
| DeleteEvent | 7,144 |
| PullRequestReviewEvent | 7,043 |
| PullRequestReviewCommentEvent | 4,275 |
| IssuesEvent | 4,135 |
| ForkEvent | 2,427 |
| ReleaseEvent | 1,099 |
| MemberEvent | 794 |
| PublicEvent | 709 |
| CommitCommentEvent | 643 |
| GollumEvent | 358 |

No duplicate `id` values within this single hour file (0 dupes measured
directly); the brief's claim of duplicates appearing *across* adjacent hour
files at the boundary could not be tested with a single hour and is taken on
trust pending the Phase 1 backfill acceptance test, which will assert
dedup correctness across a full month.

## Payload shapes for the four event types the spine metric depends on

**`PullRequestEvent`**: non-null payload keys are `action`, `number`,
`pull_request`. `action` values seen: `opened`, `closed`, `reopened`. The
full GitHub PR object is nested under `pull_request`, including
`pull_request.user.login` (the PR author) and `pull_request.created_at`.

**`PullRequestReviewEvent`**: non-null keys are `action`, `pull_request`,
`review`. `review.state` carries `approved` / `commented` / (also expected:
`changes_requested`, not seen in this sample). `review.user.login` is the
reviewer, `review.submitted_at` is the review timestamp.

**`PullRequestReviewCommentEvent`**: non-null keys are `action`,
`pull_request`, `comment`. This is a line-level review comment: `comment`
carries `pull_request_review_id`, `diff_hunk`, and `path`, confirming it is
tied to a specific review and code location, unlike a plain issue comment.

**`IssueCommentEvent`**: non-null keys are `action`, `issue`, `comment`.
Confirmed per brief section 7.1: when the comment is on a pull request (not a
plain issue), `issue.pull_request` is present and non-null (a small object
with `url`, `html_url`, `diff_url`, `patch_url`, `merged_at`). All 11,118
`IssueCommentEvent` rows in this sample hour carry a non-null
`issue.pull_request`, i.e. in this sample every issue comment happened to be
on a PR, not a bare issue. `comment.pull_request_review_id` is absent here
(that field belongs to `PullRequestReviewCommentEvent`, not this type) —
confirming `IssueCommentEvent` comments are ordinary PR conversation comments,
not line-level review comments, and must be joined through `issue.pull_request`
rather than any review-specific field.

## Bot suffix prevalence (this hour)

38,864 of 246,225 events (15.8%) come from actors whose `login` ends in
`[bot]`. This is a lower bound on true bot volume per section 7.2 (misses
pre-App-era bots running as ordinary accounts), but confirms bot traffic is
material enough that excluding it changes mart output non-trivially.

## Size extrapolation

Measured directly for one hour (2024-01-15, hour 9):

| unit | value |
|---|---|
| gzip source | 130.0 MB |
| uncompressed newline-delimited JSON | 962.3 MB |
| bronze parquet (payload as JSON text, zstd) | 92.4 MB |
| event count | 246,225 |

Bronze parquet compresses smaller than the gzip source for this hour (92.4 MB
vs 130.0 MB): zstd over columnar, mostly-repetitive URL/field text
out-compresses gzip over row-oriented JSON.

Extrapolated bronze storage, holding this hour's volume constant:

| window | hours | est. bronze parquet | est. event count |
|---|---|---|---|
| 1 day | 24 | ~2.2 GB | ~5.9 M |
| 1 month (30d) | 720 | ~66.5 GB | ~177 M |
| 1 year (365d) | 8,760 | ~810 GB | ~2.16 B |
| 3 years | 26,280 | ~2.4 TB | ~6.47 B |

This is a rough upper bound, not a forecast: it holds January 2024 hourly
volume constant across the whole range. GitHub's event volume in 2015 was
substantially lower than in 2024 (far fewer repositories and users), so an
actual 2015-2018 backfill will land well under this table's early-year
share, and the true 3-year total (if backfilling from 2015) is expected to be
meaningfully less than 3x the 1-year figure above. This table exists to
bound the decision, not to predict it precisely; given the size at 2024
volume, the initial full backfill for this project targets a small window
(1-3 months) to get the pipeline correct end-to-end before deciding whether
to extend further, rather than committing to the literal 1-3 year range
up front.
