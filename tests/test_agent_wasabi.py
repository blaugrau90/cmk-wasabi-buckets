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
        return page1 if params["pageNum"] == 0 else page2

    with patch.object(agent_wasabi, "api_get", side_effect=fake_api_get):
        records = agent_wasabi.fetch_all_records(
            "https://stats.wasabisys.com", "key", 30
        )

    assert calls == [0, 1]
    assert len(records) == agent_wasabi.PAGE_SIZE + 1


def test_fetch_all_records_stops_on_empty_page():
    with patch.object(agent_wasabi, "api_get", return_value=[]):
        records = agent_wasabi.fetch_all_records(
            "https://stats.wasabisys.com", "key", 30
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


def test_fetch_all_records_sends_no_time_filter():
    """The agent reads the API's default window completely and picks the newest record itself."""
    with patch.object(agent_wasabi, "api_get", return_value=[]) as mock_get:
        agent_wasabi.fetch_all_records("https://stats.wasabisys.com", "key", 30)

    params = mock_get.call_args.args[2]
    assert not {"from", "to", "latest"} & set(params)


def test_fetch_all_records_pages_are_zero_based_and_keep_all_buckets():
    """Regression: the Wasabi API pages are zero-based. Starting at pageNum=1 skipped the
    first 100 records, so only the tail of the list (here: the last 2 records of a
    102-record list) was seen and a bucket went missing."""
    buckets = ["example-bucket-a", "example-bucket-b", "example-bucket-c"]
    all_records = [
        {"Bucket": b, "EndTime": f"2026-10-{day:02d}T00:00:00Z"}
        for day in range(1, 35)
        for b in buckets
    ]  # 102 records, sorted by day then bucket
    assert len(all_records) == 102

    def fake_api_get(base_url, path, params, api_key, timeout):
        start = params["pageNum"] * params["pageSize"]
        return all_records[start : start + params["pageSize"]]

    with patch.object(agent_wasabi, "api_get", side_effect=fake_api_get):
        records = agent_wasabi.fetch_all_records("https://stats.wasabisys.com", "key", 30)

    assert len(records) == 102
    assert set(agent_wasabi.newest_per_bucket(records)) == set(buckets)


def test_fetch_all_records_gives_up_if_pagination_never_ends():
    full_page = [{"Bucket": "b"}] * agent_wasabi.PAGE_SIZE

    with patch.object(agent_wasabi, "api_get", return_value=full_page):
        with pytest.raises(RuntimeError, match="giving up"):
            agent_wasabi.fetch_all_records("https://stats.wasabisys.com", "key", 30)


def _rec(day: int) -> dict:
    return {"EndTime": f"2026-10-{day:02d}T00:00:00Z"}


def test_classify_buckets_flags_stale_bucket_as_obsolete():
    newest = {"live": _rec(30), "late": _rec(29), "gone": _rec(27)}

    result = {name: obsolete for name, _, obsolete in agent_wasabi.classify_buckets(newest)}

    assert result == {"live": False, "late": False, "gone": True}  # 1 day late is fine, 3 is not


def test_classify_buckets_drops_bucket_after_seven_days():
    newest = {"live": _rec(30), "gone-7d": _rec(23), "gone-8d": _rec(22)}

    names = [name for name, _, _ in agent_wasabi.classify_buckets(newest)]

    assert names == ["live", "gone-7d"]  # 7 days still shown, 8 days no longer


def test_classify_buckets_is_relative_to_api_data_not_local_clock():
    """If the whole API is behind, nothing may be flagged obsolete."""
    newest = {"a": _rec(1), "b": _rec(1)}

    assert [o for _, _, o in agent_wasabi.classify_buckets(newest)] == [False, False]


def test_classify_buckets_keeps_bucket_with_unparsable_end_time():
    newest = {"live": _rec(30), "odd": {"EndTime": "garbage"}, "none": {}}

    result = {name: obsolete for name, _, obsolete in agent_wasabi.classify_buckets(newest)}

    assert result == {"live": False, "odd": False, "none": False}
