"""Unit tests for the Wasabi bucket utilization check plugin."""

import json

from conftest import load_module

check = load_module(
    "wasabi/agent_based/wasabi_bucket_utilization.py", "wasabi_bucket_utilization"
)

def _string_table(*records):
    return [[json.dumps(record)] for record in records]


def test_parse_builds_dict_keyed_by_bucket_name():
    string_table = _string_table(
        {"bucket": "mein-bucket", "active_bytes": 100, "deleted_bytes": 5},
        {"bucket": "anderer-bucket", "active_bytes": 200, "deleted_bytes": 0},
    )

    section = check.parse_wasabi_bucket_utilization(string_table)

    assert set(section) == {"mein-bucket", "anderer-bucket"}
    assert section["mein-bucket"]["active_bytes"] == 100


def test_parse_ignores_malformed_lines():
    string_table = [["not valid json"], [json.dumps({"bucket": "ok-bucket"})]]

    section = check.parse_wasabi_bucket_utilization(string_table)

    assert set(section) == {"ok-bucket"}


def test_discovery_yields_one_service_per_bucket():
    section = {"b1": {}, "b2": {}}

    services = list(check.discover_wasabi_bucket_utilization(section))

    assert {s.item for s in services} == {"b1", "b2"}


def test_check_reports_ok_with_total_and_metrics():
    section = {"mein-bucket": {"active_bytes": 1000, "deleted_bytes": 500, "region": "eu-central-1"}}

    results = list(check.check_wasabi_bucket_utilization("mein-bucket", section))

    result = next(r for r in results if isinstance(r, check.Result))
    assert result.state == check.State.OK
    assert "eu-central-1" in result.summary

    metrics = {m.name: m.value for m in results if isinstance(m, check.Metric)}
    assert metrics == {
        "wasabi_active_bytes": 1000,
        "wasabi_deleted_bytes": 500,
        "wasabi_total_bytes": 1500,
    }


def test_check_reports_unknown_for_vanished_bucket():
    results = list(check.check_wasabi_bucket_utilization("deleted-bucket", {}))

    assert len(results) == 1
    assert results[0].state == check.State.UNKNOWN
    assert "deleted" in results[0].summary.lower() or "no longer" in results[0].summary.lower()
