import os

from airflow.sdk import Asset

GHARCHIVE_BASE_URL = "https://data.gharchive.org"
BRONZE_ASSET = Asset("bronze://gharchive_events")

MARTS_START_DATE = "2015-01-01"
ARCHIVE_START_DATE = "2011-02-12"

PR_EVENT_TYPES = (
    "PullRequestEvent",
    "PullRequestReviewEvent",
    "PullRequestReviewCommentEvent",
    "IssueCommentEvent",
)

# must match the docker-compose bronze volume mount and dbt's BRONZE_PATH var,
# or the ingest DAG writes to a path dbt's source never reads from.
BRONZE_ROOT = os.environ.get("BRONZE_ROOT", "bronze")
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get("GHARCHIVE_MAX_CONCURRENT_DOWNLOADS", "8"))
DOWNLOAD_RETRIES = 3
