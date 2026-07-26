# 005: bot exclusion combines a suffix rule and a known-bot seed

## Decision

An actor is classified as a bot if either is true:

1. `actor.login` ends in `[bot]` (the GitHub App bot convention), or
2. `actor.login` (case-insensitive, stripped of any `[bot]` suffix) appears
   in the `known_bot_actors` seed.

This logic lives in one macro, `is_bot_actor(login)`, in `dbt/macros/`, used
by every model and test that needs bot exclusion. It is not inlined as a
`WHERE actor NOT LIKE '%[bot]'` clause in individual models.

## Alternatives rejected

**Suffix rule only.** Rejected per the brief: Dependabot, Renovate, and
similar ran as ordinary user accounts before GitHub Apps existed, so a
suffix-only rule misses every pre-App-era bot event. Given the spine metric
is scoped from 2015 (over a year before GitHub Apps launched in 2016), this
would misclassify a material share of early bot activity as human review.

**Behavioral bot detection (e.g. commit/comment frequency thresholds).**
Rejected as a first pass. It is a legitimate future improvement but is
non-deterministic and expensive to justify; the seed-list approach is
auditable (a reviewer can see exactly which logins are excluded and why) and
matches how the brief scopes the requirement.

## Known false-negative rate

The seed list is a fixed, manually curated set of 13 logins. Any bot account
not in that list and not using the `[bot]` suffix is not caught. This is a
known, accepted gap: the seed is meant to cover the common, high-volume
automation accounts (dependency bots, CI bots, coverage bots), not to be an
exhaustive bot registry. Expanding the seed list is the expected maintenance
path when new bot accounts are identified in the data.

## Consequence

`fct_pr_review_latency` and any mart computing "human" review or contribution
must join through `is_bot_actor` and exclude bot actors explicitly; this is
enforced by a singular test (`assert_no_bot_reviews_counted_as_human`) rather
than left to code review.
