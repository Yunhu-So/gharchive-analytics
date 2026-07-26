from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import duckdb
from airflow.decorators import task
from airflow.sdk import DAG
from airflow.models.pool import Pool

from utils.constants import BRONZE_ASSET, BRONZE_ROOT, MAX_CONCURRENT_DOWNLOADS
from utils.fetch import MissingHourError, fetch_hour

logger = logging.getLogger(__name__)

DOWNLOAD_POOL = "gharchive_download_pool"
MISSING_HOURS_DB = os.path.join(BRONZE_ROOT, "_control", "missing_hours.duckdb")


def _ensure_pool() -> None:
    from airflow.utils.session import create_session

    with create_session() as session:
        if not Pool.get_pool(DOWNLOAD_POOL, session=session):
            session.add(
                Pool(
                    pool=DOWNLOAD_POOL,
                    slots=MAX_CONCURRENT_DOWNLOADS,
                    description="caps concurrent GH Archive downloads during backfill",
                )
            )


_ensure_pool()

with DAG(
    dag_id="gharchive_ingest",
    schedule="@daily",
    start_date=datetime(2015, 1, 1),
    catchup=True,
    max_active_runs=3,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
    },
    tags=["ingest", "bronze"],
) as dag:

    @task
    def list_hours(logical_date=None) -> list[int]:
        return list(range(24))

    @task(pool=DOWNLOAD_POOL, max_active_tis_per_dag=MAX_CONCURRENT_DOWNLOADS)
    def fetch_and_land_hour(hour: int, logical_date=None) -> dict:
        dt = logical_date.strftime("%Y-%m-%d")
        partition_dir = os.path.join(BRONZE_ROOT, f"dt={dt}", f"hour={hour:02d}")

        try:
            raw = fetch_hour(dt, hour, dest_dir=os.path.join(BRONZE_ROOT, "_raw", dt))
        except MissingHourError as exc:
            _record_missing_hour(dt, hour, reason="404_not_found", detail=str(exc))
            logger.info("hour %s-%s does not exist upstream, recorded and skipping", dt, hour)
            return {"dt": dt, "hour": hour, "status": "missing"}

        _write_partition_atomically(raw.local_path, partition_dir)
        return {"dt": dt, "hour": hour, "status": "landed"}

    @task(outlets=[BRONZE_ASSET])
    def assert_all_hours_processed(results: list[dict]) -> None:
        landed = sum(1 for r in results if r["status"] == "landed")
        missing = sum(1 for r in results if r["status"] == "missing")
        logger.info("landed=%s missing=%s total=%s", landed, missing, len(results))

    hours = list_hours()
    results = fetch_and_land_hour.expand(hour=hours)
    assert_all_hours_processed(results)


def _write_partition_atomically(raw_gz_path: str, partition_dir: str) -> None:
    tmp_dir = partition_dir + ".tmp"
    os.makedirs(os.path.dirname(tmp_dir) or ".", exist_ok=True)
    if os.path.exists(tmp_dir):
        _rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)

    con = duckdb.connect()
    try:
        con.execute(
            """
            copy (
                select
                    id,
                    type,
                    actor,
                    repo,
                    org,
                    created_at,
                    to_json(payload) as payload
                from read_json(?, format='newline_delimited', union_by_name=true)
            ) to ? (format parquet, compression zstd)
            """,
            [raw_gz_path, os.path.join(tmp_dir, "part-0.parquet")],
        )
    finally:
        con.close()

    if os.path.exists(partition_dir):
        _rmtree(partition_dir)
    os.replace(tmp_dir, partition_dir)


def _rmtree(path: str) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)


def _record_missing_hour(dt: str, hour: int, reason: str, detail: str) -> None:
    os.makedirs(os.path.dirname(MISSING_HOURS_DB), exist_ok=True)
    con = duckdb.connect(MISSING_HOURS_DB)
    try:
        con.execute(
            """
            create table if not exists missing_hours (
                dt varchar,
                hour integer,
                reason varchar,
                detail varchar,
                recorded_at timestamp default current_timestamp,
                primary key (dt, hour)
            )
            """
        )
        con.execute(
            """
            insert into missing_hours (dt, hour, reason, detail)
            values (?, ?, ?, ?)
            on conflict (dt, hour) do update set
                reason = excluded.reason,
                detail = excluded.detail,
                recorded_at = current_timestamp
            """,
            [dt, hour, reason, detail],
        )
    finally:
        con.close()
