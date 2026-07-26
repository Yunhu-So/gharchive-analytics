from __future__ import annotations

import gzip
import logging
import os
import tempfile
import time
from dataclasses import dataclass

import requests

from .constants import DOWNLOAD_RETRIES, GHARCHIVE_BASE_URL

logger = logging.getLogger(__name__)


class MissingHourError(Exception):
    """Raised when GH Archive returns 404 for an hour: the hour genuinely does not exist."""


@dataclass
class FetchResult:
    dt: str
    hour: int
    url: str
    local_path: str


def gharchive_url(dt: str, hour: int, base_url: str = GHARCHIVE_BASE_URL) -> str:
    # the hour segment is NOT zero-padded: .../2024-01-15-9.json.gz, not -09-
    return f"{base_url}/{dt}-{hour}.json.gz"


def fetch_hour(dt: str, hour: int, dest_dir: str, base_url: str = GHARCHIVE_BASE_URL) -> FetchResult:
    url = gharchive_url(dt, hour, base_url)
    last_exc: Exception | None = None

    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            response = requests.get(url, stream=True, timeout=60)
        except requests.RequestException as exc:
            last_exc = exc
            _backoff(attempt)
            continue

        if response.status_code == 404:
            raise MissingHourError(f"{url} returned 404: hour not present in archive")

        if response.status_code >= 500:
            last_exc = RuntimeError(f"{url} returned {response.status_code}")
            _backoff(attempt)
            continue

        response.raise_for_status()

        os.makedirs(dest_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dest_dir, suffix=".json.gz.tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            _validate_gzip(tmp_path)
        except Exception as exc:
            os.remove(tmp_path)
            last_exc = exc
            _backoff(attempt)
            continue

        final_path = os.path.join(dest_dir, f"{dt}-{hour}.json.gz")
        os.replace(tmp_path, final_path)
        return FetchResult(dt=dt, hour=hour, url=url, local_path=final_path)

    raise RuntimeError(f"failed to fetch {url} after {DOWNLOAD_RETRIES} attempts") from last_exc


def _validate_gzip(path: str) -> None:
    with gzip.open(path, "rb") as f:
        while f.read(1024 * 1024):
            pass


def _backoff(attempt: int) -> None:
    time.sleep(2**attempt)
