"""One-off adapter demonstrating ingestion of pre-2015 GH Archive data.

Not wired into the gharchive_ingest DAG: the Timeline API predates the
Events API and has a different event vocabulary (see ADR 004). This is a
bounded demonstration for one month, not a basis for extending the spine
metric backward. Run directly: `python -m utils.timeline_adapter 2014-06`.
"""

from __future__ import annotations

import calendar
import os
import sys
from datetime import date

import duckdb

from .constants import GHARCHIVE_BASE_URL
from .fetch import MissingHourError, fetch_hour

TIMELINE_BRONZE_ROOT = os.environ.get("TIMELINE_BRONZE_ROOT", "bronze_timeline")


def ingest_month(year: int, month: int, dest_root: str = TIMELINE_BRONZE_ROOT) -> None:
    _, days_in_month = calendar.monthrange(year, month)
    for day in range(1, days_in_month + 1):
        dt = date(year, month, day).isoformat()
        for hour in range(24):
            _ingest_hour(dt, hour, dest_root)


def _ingest_hour(dt: str, hour: int, dest_root: str) -> None:
    partition_dir = os.path.join(dest_root, f"dt={dt}", f"hour={hour:02d}")
    final_path = os.path.join(partition_dir, "part-0.parquet")
    if os.path.exists(final_path):
        return

    try:
        raw = fetch_hour(
            dt, hour, dest_dir=os.path.join(dest_root, "_raw", dt), base_url=GHARCHIVE_BASE_URL
        )
    except MissingHourError:
        return

    os.makedirs(partition_dir, exist_ok=True)
    tmp_path = os.path.join(partition_dir, ".part-0.parquet.tmp")
    escaped_tmp_path = tmp_path.replace("'", "''")

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            copy (
                select
                    -- the Timeline API has no event id at all: synthesize
                    -- one from fields that together identify an event.
                    -- created_at/actor/url alone collide often (many
                    -- events from the same actor to the same url within
                    -- the same second), so the payload is included too.
                    md5(created_at::varchar || actor || url || to_json(payload)) as id,
                    type,
                    struct_pack(id := NULL::bigint, login := actor) as actor,
                    struct_pack(
                        id := repository.id,
                        name := repository.name,
                        url := repository.url
                    ) as repo,
                    NULL::struct(id bigint, login varchar) as org,
                    created_at,
                    to_json(payload) as payload
                from read_json(?, format='newline_delimited', union_by_name=true)
            ) to '{escaped_tmp_path}' (format parquet, compression zstd)
            """,
            [raw.local_path],
        )
    finally:
        con.close()

    os.replace(tmp_path, final_path)


if __name__ == "__main__":
    if len(sys.argv) != 2 or len(sys.argv[1]) != 7:
        print("usage: python -m utils.timeline_adapter YYYY-MM", file=sys.stderr)
        sys.exit(1)
    year_str, month_str = sys.argv[1].split("-")
    ingest_month(int(year_str), int(month_str))
