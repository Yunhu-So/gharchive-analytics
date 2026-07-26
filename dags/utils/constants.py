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

BRONZE_ROOT = "bronze"
MAX_CONCURRENT_DOWNLOADS = 8
DOWNLOAD_RETRIES = 3
