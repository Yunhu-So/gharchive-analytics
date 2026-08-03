# 004: marts scoped to 2015+, Timeline API adapter as a bounded demo only

## Decision

All marts are scoped to `created_at >= '2015-01-01'` via the
`marts_start_date` dbt var. Archives before that date come from the
deprecated GitHub Timeline API, which predates the Events API entirely and
uses a different event vocabulary and payload shape (not a renamed or
restructured version of the same events; a genuinely different API).

A Timeline API adapter is implemented for exactly one month of 2014 data
(`stg_timeline__*` models, gated behind a separate seed/source rather than
mixed into the 2015+ staging models) as a demonstration that the schema break
is understood and bridgeable, not as a basis for extending the spine metric
backward.

## Alternatives rejected

**Extend marts back to 2011 by mapping Timeline API events onto the Events
API vocabulary.** Rejected as the default scope. The Timeline API's event
types do not have a clean 1:1 mapping onto `PullRequestReviewEvent` /
`PullRequestReviewCommentEvent` semantics used by the spine metric; forcing a
mapping would either silently drop information or require encoding
assumptions about 2011-2014 GitHub review workflows that cannot be verified
against the current API's semantics. Doing this for the full pre-2015 range
was judged higher-risk than valuable, given GitHub's PR review feature
(formal reviews, as opposed to plain comments) did not exist in anything
like its current form that early.

**Ignore pre-2015 data entirely, no adapter at all.** Rejected because the
brief requires demonstrating that the schema break is handled, not just
documented. The one-month adapter exists to prove the ingestion and staging
pattern extends across the break, without committing to the accuracy work
required to make pre-2015 data mart-eligible.

## Implementation notes

Fetched against real 2014-06 data (`dags/utils/timeline_adapter.py`, one
month, run standalone rather than through `gharchive_ingest`). Two concrete
differences from the Events API confirmed the schema break is real, not
theoretical:

- there is no event `id` at all; the adapter synthesizes one by hashing
  `created_at || actor || url`, which can collide for two events from the
  same actor to the same repo within the same second (a real, accepted
  limitation of a bounded demo, not something worth engineering around)
- `actor` is a bare login string with no stable numeric id (`actor_attributes`
  carries login, name, company, etc., but never an id) — repos have one,
  actors don't, which is itself informative about why identity tracking
  across renames (ADR on snapshots) is a 2015+-only concern

## Consequence

Any question about GitHub activity before 2015 is out of scope for this
project's marts. The 2014 adapter's output is not unioned into any
2015+ staging or mart model.
