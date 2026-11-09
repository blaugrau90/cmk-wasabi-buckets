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


def test_account_discovery_yields_single_service_when_buckets_exist():
    section = {"b1": {}, "b2": {}}

    services = list(check.discover_wasabi_account_utilization(section))

    assert len(services) == 1
    assert services[0].item is None


def test_account_discovery_yields_nothing_for_empty_section():
    services = list(check.discover_wasabi_account_utilization({}))

    assert services == []


def test_account_check_sums_across_all_buckets():
    section = {
        "bucket-one": {"active_bytes": 1000, "deleted_bytes": 500},
        "bucket-two": {"active_bytes": 2000, "deleted_bytes": 0},
    }

    results = list(check.check_wasabi_account_utilization(section))

    result = next(r for r in results if isinstance(r, check.Result))
    assert result.state == check.State.OK
    assert "2 buckets" in result.summary

    metrics = {m.name: m.value for m in results if isinstance(m, check.Metric)}
    assert metrics == {
        "wasabi_active_bytes": 3000,
        "wasabi_deleted_bytes": 500,
        "wasabi_total_bytes": 3500,
    }


def test_account_check_reports_unknown_when_no_buckets():
    results = list(check.check_wasabi_account_utilization({}))

    assert len(results) == 1
    assert results[0].state == check.State.UNKNOWN


def test_obsolete_bucket_is_not_discovered():
    section = {"live": {"active_bytes": 1}, "gone": {"obsolete": True, "end_time": "2026-10-18T00:00:00Z"}}

    services = list(check.discover_wasabi_bucket_utilization(section))

    assert {s.item for s in services} == {"live"}


def test_obsolete_bucket_reports_warn_without_metrics():
    section = {"gone": {"obsolete": True, "end_time": "2026-10-18T00:00:00Z", "active_bytes": 0}}

    results = list(check.check_wasabi_bucket_utilization("gone", section))

    assert len(results) == 1
    assert results[0].state == check.State.WARN
    assert "2026-10-18" in results[0].summary
    assert "Obsolete" in results[0].summary


def test_account_total_excludes_obsolete_buckets():
    section = {
        "live": {"active_bytes": 100, "deleted_bytes": 10},
        "gone": {"active_bytes": 999, "deleted_bytes": 999, "obsolete": True},
    }

    results = list(check.check_wasabi_account_utilization(section))

    metrics = {r.name: r.value for r in results if isinstance(r, check.Metric)}
    assert metrics["wasabi_total_bytes"] == 110
    assert "across 1 bucket" in next(r for r in results if isinstance(r, check.Result)).summary


def test_account_service_not_discovered_if_only_obsolete_buckets():
    assert list(check.discover_wasabi_account_utilization({"gone": {"obsolete": True}})) == []
