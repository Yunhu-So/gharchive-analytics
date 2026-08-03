import json
import os
import subprocess
from datetime import timedelta
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).parent.parent
DBT_DIR = REPO_ROOT / "dbt"
BRONZE_DIR = REPO_ROOT / "bronze"

# PullRequestEvent payloads embed GitHub's full nested pull_request object
# (averaging ~16 KB, up to 250+ KB per row on the real backfill; see ADR
# 001). Proving incremental output matches a full refresh doesn't need the
# whole growing backfill, just a real window of it, so this scopes both
# builds to the most recent few days actually ingested rather than
# whatever the backfill has grown to by the time this runs.
RECENT_WINDOW_DAYS = 1


def _dbt(args, duckdb_path, extra_vars=None):
    # each duckdb file gets its own DBT_TARGET_PATH: dbt's partial-parse
    # cache under dbt/target/ is keyed by project state, not by DUCKDB_PATH,
    # so the full-refresh and incremental runs in this test sharing the
    # default target dir means the second run's ref() calls can resolve
    # against the first run's duckdb catalog name instead of its own.
    target_path = duckdb_path.parent / f"target_{duckdb_path.stem}"
    env = {
        **os.environ,
        "DUCKDB_PATH": str(duckdb_path),
        "DBT_TARGET_PATH": str(target_path),
    }
    full_args = ["dbt", *args, "--target", "dev"]
    if extra_vars:
        full_args += ["--vars", json.dumps(extra_vars)]
    result = subprocess.run(
        full_args,
        cwd=DBT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"dbt {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
        )


def _recent_window_start():
    con = duckdb.connect()
    (max_dt,) = con.execute(
        f"select max(dt) from read_parquet('{BRONZE_DIR}/dt=*/hour=*/*.parquet', "
        "hive_partitioning=true, union_by_name=true)"
    ).fetchone()
    con.close()
    return (max_dt - timedelta(days=RECENT_WINDOW_DAYS)).isoformat()


def _lifecycle_rows(duckdb_path):
    con = duckdb.connect(str(duckdb_path))
    rows = con.execute(
        """
        select repo_id, pr_number, pr_author_id, opened_at, first_review_at,
               is_first_time_contributor, is_first_contributor_uncertain
        from main_intermediate.int_pr_lifecycle
        order by repo_id, pr_number
        """
    ).fetchall()
    con.close()
    return rows


@pytest.mark.skipif(
    not (REPO_ROOT / "bronze").exists(),
    reason="requires bronze data from a completed ingest run",
)
@pytest.mark.skipif(
    os.environ.get("RUN_SLOW_TESTS") != "1",
    reason=(
        "opt-in: builds two real dbt warehouses from ingested data (two "
        "dbt invocations each running deps/seed/full-refresh, plus one "
        "incremental rerun) rather than mocking anything, so it takes tens "
        "of seconds. Set RUN_SLOW_TESTS=1 to run it."
    ),
)
def test_incremental_run_matches_full_refresh(tmp_path):
    full_refresh_db = tmp_path / "full_refresh.duckdb"
    # rerun_db never changes path between its full-refresh build and its
    # incremental rerun below: dbt-duckdb's connection environment is a
    # process-wide singleton keyed by credentials (see
    # DuckDBConnectionManager._ENV) that reopens its handle lazily and
    # caches the resolved catalog name from whichever path first created
    # it, so copying a built database to a differently-named/pathed file
    # and pointing DUCKDB_PATH at the copy makes dbt resolve ref()s against
    # the ORIGINAL path's catalog instead of the copy's -- reproduced even
    # with the same basename in a different directory. Keeping one path
    # throughout sidesteps that entirely and also matches how the real
    # backfill actually runs incrementally: same file, never renamed.
    rerun_db = tmp_path / "rerun.duckdb"
    scope = {"marts_start_date": _recent_window_start()}

    # int_pr_lifecycle depends only on staging models and the bot seed, not
    # dim_repo/dim_actor (those are expensive arg_max aggregations over the
    # whole event history this test has no reason to pay for). Using `run`
    # rather than `build` also skips re-running the generic staging tests,
    # already proven correct in CI against the fixture: this test's purpose
    # is the incremental/full-refresh comparison, not re-verifying those.
    for db in (full_refresh_db, rerun_db):
        _dbt(["deps"], db)
        _dbt(["seed"], db)
        _dbt(["run", "--full-refresh", "--select", "+int_pr_lifecycle"], db, scope)
    full_refresh_result = _lifecycle_rows(full_refresh_db)

    # rerun incrementally against the identical source data: no new PRs exist
    # to process, so this only exercises the "still open, recheck within
    # max_age" branch. The result must be byte-identical to the full refresh.
    _dbt(["run", "--select", "int_pr_lifecycle"], rerun_db, scope)
    incremental_result = _lifecycle_rows(rerun_db)

    assert full_refresh_result == incremental_result
    assert len(full_refresh_result) > 0
