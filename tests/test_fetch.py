import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "dags"))

from utils.fetch import gharchive_url


def test_hour_is_not_zero_padded():
    assert gharchive_url("2024-01-15", 9) == "https://data.gharchive.org/2024-01-15-9.json.gz"


def test_double_digit_hour_unaffected():
    assert gharchive_url("2024-01-15", 14) == "https://data.gharchive.org/2024-01-15-14.json.gz"
