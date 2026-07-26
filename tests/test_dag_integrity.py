import importlib
import os
import sys

import pytest

DAGS_DIR = os.path.join(os.path.dirname(__file__), "..", "dags")
DAG_MODULES = ["gharchive_ingest", "gharchive_transform"]


@pytest.fixture(autouse=True, scope="module")
def _dags_on_path():
    sys.path.insert(0, os.path.abspath(DAGS_DIR))
    yield
    sys.path.remove(os.path.abspath(DAGS_DIR))


@pytest.mark.parametrize("module_name", DAG_MODULES)
def test_dag_module_imports_without_error(module_name):
    module = importlib.import_module(module_name)
    dag = getattr(module, "dag", None)
    assert dag is not None, f"{module_name} does not expose a module-level `dag`"


@pytest.mark.parametrize("module_name", DAG_MODULES)
def test_dag_has_no_cycles(module_name):
    module = importlib.import_module(module_name)
    dag = module.dag
    dag.test_cycle()
