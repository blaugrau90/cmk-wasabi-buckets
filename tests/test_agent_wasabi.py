"""Unit tests for the Wasabi special agent script (pagination + newest-record logic)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import load_module

agent_wasabi = load_module("wasabi/libexec/agent_wasabi", "agent_wasabi")

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bucket_utilization_sample.json"


def test_newest_per_bucket_picks_latest_end_time():
    records = [
        {"Bucket": "b1", "EndTime": "2026-09-24T00:00:00Z", "RawStorageSizeBytes": 100},
        {"Bucket": "b1", "EndTime": "2026-09-25T00:00:00Z", "RawStorageSizeBytes": 200},
        {"Bucket": "b2", "EndTime": "2026-09-25T00:00:00Z", "RawStorageSizeBytes": 50},
    ]

    result = agent_wasabi.newest_per_bucket(records)

    assert set(result) == {"b1", "b2"}
    assert result["b1"]["RawStorageSizeBytes"] == 200
    assert result["b2"]["RawStorageSizeBytes"] == 50


def test_newest_per_bucket_skips_records_without_bucket_name():
    records = [{"EndTime": "2026-09-25T00:00:00Z", "RawStorageSizeBytes": 999}]

    result = agent_wasabi.newest_per_bucket(records)

    assert result == {}


def test_fetch_all_records_paginates_until_short_page():
    page1 = [{"Bucket": f"bucket-{i}"} for i in range(agent_wasabi.PAGE_SIZE)]
    page2 = [{"Bucket": "last-bucket"}]

    calls = []

    def fake_api_get(base_url, path, params, api_key, timeout):
        calls.append(params["pageNum"])
        return page1 if params["pageNum"] == 1 else page2

    with patch.object(agent_wasabi, "api_get", side_effect=fake_api_get):
        records = agent_wasabi.fetch_all_records(
            "https://stats.wasabisys.com", "key", "2026-09-23", "2026-09-25", 30
        )

    assert calls == [1, 2]
    assert len(records) == agent_wasabi.PAGE_SIZE + 1


def test_fetch_all_records_stops_on_empty_page():
    with patch.object(agent_wasabi, "api_get", return_value=[]):
        records = agent_wasabi.fetch_all_records(
            "https://stats.wasabisys.com", "key", "2026-09-23", "2026-09-25", 30
        )

    assert records == []


def test_api_get_raises_runtime_error_on_connection_failure():
    import urllib.error

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        with pytest.raises(RuntimeError, match="Connection error"):
            agent_wasabi.api_get(
                "https://stats.wasabisys.com", "/v1/standalone/utilizations/bucket",
                {}, "key", 5,
            )


def test_api_get_unwraps_real_wasabi_page_info_envelope():
    """Regression test using the real API response shape reported by the user:
    {"PageInfo": {...}, "Records": [...]} - not a bare list or a lowercase key."""

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return FIXTURE_PATH.read_bytes()

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        records = agent_wasabi.api_get(
            "https://stats.wasabisys.com", "/v1/standalone/utilizations/bucket",
            {"pageSize": 10, "pageNum": 1}, "access:secret", 5,
        )

    assert len(records) == 6
    assert {r["Bucket"] for r in records} == {
        "example-bucket-deleted", "example-bucket-one", "example-bucket-two", "example-bucket-three",
    }


def test_newest_per_bucket_on_real_fixture_picks_latest_snapshot():
    records = json.loads(FIXTURE_PATH.read_text())["Records"]

    result = agent_wasabi.newest_per_bucket(records)

    assert result["example-bucket-one"]["EndTime"] == "2026-09-06T00:00:00Z"
    assert result["example-bucket-one"]["RawStorageSizeBytes"] == 803743727143


def test_api_get_raises_runtime_error_on_invalid_json():
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"not json"

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        with pytest.raises(RuntimeError, match="Invalid JSON"):
            agent_wasabi.api_get(
                "https://stats.wasabisys.com", "/v1/standalone/utilizations/bucket",
                {}, "key", 5,
            )
