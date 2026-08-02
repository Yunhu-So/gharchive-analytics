# 003: int_pr_lifecycle uses a 90-day lookback window, not a partition-only incremental

## Decision

`int_pr_lifecycle` is materialized incrementally, keyed on `unique_key =
(repo_id, pr_number)`. On each incremental run it reprocesses:

- every PR newly opened since the last run, and
- every PR already in the table that still lacks a `first_review_at`,
  as long as it was opened within `pr_lifecycle_max_age_days` (default 365)
  of now.

A PR drops out of the reprocessing set once it has a `first_review_at`, or
once it exceeds the max-age cutoff, whichever comes first. Max-age exists so
a PR left open indefinitely does not force this model to rescan it forever;
past that age its lifecycle is treated as final even if a review lands
later. This is a deliberate accuracy tradeoff, not an oversight.

`pr_lifecycle_lookback_days` (default 90) is a second, narrower knob: it
bounds how far back the model scans review/comment events when computing
`first_review_at` for the reprocessing set, as a safety margin beyond
`max_age_days` against clock skew rather than a second eligibility gate.
Eligibility itself is governed by `max_age_days` alone — a PR is either
still being watched for its first review or it has aged out; there is no
window where it is watched only sometimes.

## Why a lookback window at all

A PR opened in January may not receive its first review until March. A
naive incremental model that only scans the current run's partition for new
`PullRequestReviewEvent`/`PullRequestReviewCommentEvent`/qualifying
`IssueCommentEvent` rows will never attach that March review back to the
January PR row, because the January row was already written and the model
never revisits it. The spine metric (open-to-first-review latency) would
silently undercount long-lived PRs and skew toward reporting only fast
reviews.

## Alternatives rejected

**Full refresh every run.** Correct, but throws away the incremental
model's entire point: reprocessing years of PR history on every run does not
scale with backfill size, and CI would rebuild the whole history on every
PR.

**Unbounded lookback (rescan all historically open PRs, no cutoff).**
Rejected because a PR that never closes (abandoned, or a bot-created branch
left open) would stay in the reprocessing set forever, and the incremental
run's cost would grow monotonically with the age of the dataset instead of
staying bounded.

**Rely on a separate "reopen" signal to trigger reprocessing instead of a
time window.** GH Archive does not reliably expose a clean signal for
"this PR just received a delayed first review" independent of scanning
review events themselves, so there is nothing cheaper to key off than the
event stream already being read for staging.

## Verification

A singular test (`assert_first_review_after_opened`) asserts no row has
`first_review_at < opened_at`. A separate test compares a full-refresh build
against an incremental build over the same historical window and asserts row-
for-row equality, proving the lookback window does not produce different
results than reprocessing everything would.
