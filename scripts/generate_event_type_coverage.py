"""Generates docs/event_type_coverage.md from the actual ingested bronze data.

Run after a backfill covers a meaningful span:
    .venv/bin/python scripts/generate_event_type_coverage.py
"""

from __future__ import annotations

import os

import duckdb

BRONZE_PATH = os.environ.get("BRONZE_PATH", "bronze")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "event_type_coverage.md")

# GitHub's current Events API type list (docs.github.com/en/developers/webhooks-and-events/
# github-event-types). Some of these were added well after 2011 (PullRequestReviewEvent
# shipped with GitHub's 2016 formal-review-UI launch); a type present here but absent from
# a given ingested range is expected, not a data gap, if the range predates its launch.
KNOWN_EVENT_TYPES = {
    "CommitCommentEvent",
    "CreateEvent",
    "DeleteEvent",
    "ForkEvent",
    "GollumEvent",
    "IssueCommentEvent",
    "IssuesEvent",
    "MemberEvent",
    "PublicEvent",
    "PullRequestEvent",
    "PullRequestReviewEvent",
    "PullRequestReviewCommentEvent",
    "PullRequestReviewThreadEvent",
    "PushEvent",
    "ReleaseEvent",
    "SponsorshipEvent",
    "WatchEvent",
}


def main() -> None:
    con = duckdb.connect()
    rows = con.execute(
        f"""
        select
            type,
            min(created_at) as first_seen,
            max(created_at) as last_seen,
            count(*) as event_count
        from read_parquet('{BRONZE_PATH}/dt=*/hour=*/*.parquet', hive_partitioning=true, union_by_name=true)
        group by type
        order by first_seen
        """
    ).fetchall()

    ingested_range = con.execute(
        f"""
        select min(created_at), max(created_at)
        from read_parquet('{BRONZE_PATH}/dt=*/hour=*/*.parquet', hive_partitioning=true, union_by_name=true)
        """
    ).fetchone()

    lines = [
        "# Event type coverage",
        "",
        f"Generated from ingested bronze data spanning "
        f"{ingested_range[0]} to {ingested_range[1]}.",
        "",
        "| type | first seen | last seen | event count |",
        "|---|---|---|---|",
    ]
    for type_, first_seen, last_seen, count in rows:
        lines.append(f"| {type_} | {first_seen} | {last_seen} | {count:,} |")

    lines += [
        "",
        "A type whose first-seen date falls after the ingested range's start "
        "entered the Events API later than that point; a type whose "
        "last-seen date falls before the range's end stopped being emitted "
        "before that point. Either case means a time series spanning that "
        "type's absence would misread instrumentation change as a real "
        "trend (see README caveats and section 7.3 of the build brief).",
    ]

    missing_types = sorted(KNOWN_EVENT_TYPES - {type_ for type_, *_ in rows})
    if missing_types:
        lines += [
            "",
            "## Known event types absent from this range",
            "",
            "Zero events of these types appear anywhere in the ingested "
            "range above. For a type that launched after this range's end "
            "(e.g. PullRequestReviewEvent, which GitHub introduced with its "
            "2016 formal-review UI), this is expected, not a gap -- confirm "
            "against GitHub's own type history before treating it as one:",
            "",
        ]
        lines += [f"- {type_}" for type_ in missing_types]

    lines += [""]

    with open(OUTPUT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
