"""Generates docs/event_type_coverage.md from the actual ingested bronze data.

Run after a backfill covers a meaningful span:
    .venv/bin/python scripts/generate_event_type_coverage.py
"""

from __future__ import annotations

import os

import duckdb

BRONZE_PATH = os.environ.get("BRONZE_PATH", "bronze")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "event_type_coverage.md")


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

    with open(OUTPUT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
