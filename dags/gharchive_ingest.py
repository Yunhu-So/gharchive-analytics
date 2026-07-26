from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import duckdb
from airflow.decorators import task
from airflow.sdk import DAG
from utils.constants import BRONZE_ASSET, BRONZE_ROOT, MAX_CONCURRENT_DOWNLOADS
from utils.fetch import MissingHourError, fetch_hour

logger = logging.getLogger(__name__)

# created by airflow-init in docker-compose.yml, not at DAG parse time:
# parsing must not require a live, migrated metadata DB (breaks
# tests/test_dag_integrity.py and any plain `dbt`/`pytest` invocation).
DOWNLOAD_POOL = "gharchive_download_pool"
MISSING_HOURS_DB = os.path.join(BRONZE_ROOT, "_control", "missing_hours.duckdb")

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
    # os.replace is only atomic at the file level (a directory-to-directory
    # replace can't be done without a brief window where the target is
    # missing, since POSIX rename requires an empty or absent directory
    # target). Each hour is exactly one file, so write under a temp name
    # and rename just that file into place.
    os.makedirs(partition_dir, exist_ok=True)
    tmp_path = os.path.join(partition_dir, ".part-0.parquet.tmp")
    final_path = os.path.join(partition_dir, "part-0.parquet")

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
            [raw_gz_path, tmp_path],
        )
    finally:
        con.close()

    os.replace(tmp_path, final_path)


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
