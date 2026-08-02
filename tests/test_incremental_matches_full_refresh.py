import os
import shutil
import subprocess
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).parent.parent
DBT_DIR = REPO_ROOT / "dbt"


def _dbt(args, duckdb_path):
    env = {**os.environ, "DUCKDB_PATH": str(duckdb_path)}
    subprocess.run(
        ["dbt", *args, "--target", "dev"],
        cwd=DBT_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


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
def test_incremental_run_matches_full_refresh(tmp_path):
    full_refresh_db = tmp_path / "full_refresh.duckdb"
    incremental_db = tmp_path / "incremental.duckdb"

    _dbt(["deps"], full_refresh_db)
    _dbt(["seed"], full_refresh_db)
    _dbt(["run", "--select", "staging.*", "marts.dim_repo", "marts.dim_actor"], full_refresh_db)
    _dbt(["run", "--full-refresh", "--select", "int_pr_lifecycle"], full_refresh_db)
    full_refresh_result = _lifecycle_rows(full_refresh_db)

    shutil.copy(full_refresh_db, incremental_db)
    # rerun incrementally against the identical source data: no new PRs exist
    # to process, so this only exercises the "still open, recheck within
    # max_age" branch. The result must be byte-identical to the full refresh.
    _dbt(["run", "--select", "int_pr_lifecycle"], incremental_db)
    incremental_result = _lifecycle_rows(incremental_db)

    assert full_refresh_result == incremental_result
    assert len(full_refresh_result) > 0
