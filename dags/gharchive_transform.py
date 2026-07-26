from __future__ import annotations

import os

from cosmos import DbtDag, ProjectConfig, ProfileConfig, RenderConfig, ExecutionConfig
from cosmos.constants import LoadMode

from utils.constants import BRONZE_ASSET

DBT_PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..", "dbt")

profile_config = ProfileConfig(
    profile_name="gharchive",
    target_name=os.environ.get("DBT_TARGET", "dev"),
    profiles_yml_filepath=os.path.join(DBT_PROJECT_DIR, "profiles.yml"),
)

project_config = ProjectConfig(
    dbt_project_path=DBT_PROJECT_DIR,
    env_vars={"DUCKDB_PATH": os.environ.get("DUCKDB_PATH", "")},
)

render_config = RenderConfig(load_method=LoadMode.DBT_LS)
execution_config = ExecutionConfig(dbt_executable_path=os.environ.get("DBT_EXECUTABLE_PATH", "dbt"))

dag = DbtDag(
    dag_id="gharchive_transform",
    project_config=project_config,
    profile_config=profile_config,
    render_config=render_config,
    execution_config=execution_config,
    schedule=[BRONZE_ASSET],
    tags=["transform", "dbt"],
)
