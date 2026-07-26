.PHONY: setup run stop clean test lint dbt-build dbt-test backfill

VENV := .venv/bin

AIRFLOW_VERSION := 3.3.0
PYTHON_VERSION := 3.12
CONSTRAINT_URL := https://raw.githubusercontent.com/apache/airflow/constraints-$(AIRFLOW_VERSION)/constraints-$(PYTHON_VERSION).txt

setup:
	test -f .env || cp .env.example .env
	python3.12 -m venv .venv
	$(VENV)/pip install --upgrade pip -q
	$(VENV)/pip install "apache-airflow==$(AIRFLOW_VERSION)" --constraint "$(CONSTRAINT_URL)" -q
	$(VENV)/pip install -r requirements-dev.txt -q
	$(VENV)/dbt deps --project-dir dbt

run:
	docker compose up -d --wait
	docker compose exec airflow-apiserver airflow dags unpause gharchive_ingest
	docker compose exec airflow-apiserver airflow dags unpause gharchive_transform
	docker compose exec airflow-apiserver airflow dags trigger gharchive_ingest

stop:
	docker compose down

clean:
	docker compose down -v
	rm -rf bronze logs .venv dbt/target dbt/dbt_packages gharchive.duckdb

lint:
	$(VENV)/ruff check dags tests
	$(VENV)/sqlfluff lint dbt/models dbt/snapshots

test:
	$(VENV)/pytest tests/

dbt-build:
	cd dbt && DUCKDB_PATH=../gharchive.duckdb ../$(VENV)/dbt build

dbt-test:
	cd dbt && DUCKDB_PATH=../gharchive.duckdb ../$(VENV)/dbt test

backfill:
	docker compose exec airflow-apiserver airflow dags backfill gharchive_ingest \
		--start-date $(START) --end-date $(END)
