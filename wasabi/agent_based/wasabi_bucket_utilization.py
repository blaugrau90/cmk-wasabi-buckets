#!/usr/bin/env python3
"""Checkmk agent-based check plugin for Wasabi bucket storage utilization.

Section: wasabi_bucket_utilization
One JSON object per line, keyed by bucket name.

There are no thresholds - Wasabi utilization has no notion of "too much" or
"too little" from a monitoring perspective, so the check is purely
informational (always OK) and exposes metrics for graphing.
"""

import json
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    render,
)


def parse_wasabi_bucket_utilization(string_table: StringTable) -> dict[str, Any]:
    """Parse agent section into a dict keyed by bucket name."""
    buckets: dict[str, Any] = {}
    for row in string_table:
        if not row:
            continue
        try:
            record = json.loads(row[0])
            name = record.get("bucket")
            if name:
                buckets[name] = record
        except (json.JSONDecodeError, KeyError):
            pass
    return buckets


def discover_wasabi_bucket_utilization(section: dict[str, Any]) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_wasabi_bucket_utilization(item: str, section: dict[str, Any]) -> CheckResult:
    bucket = section.get(item)
    if bucket is None:
        yield Result(
            state=State.UNKNOWN,
            summary="Bucket no longer reported by the Wasabi API (may have been deleted)",
        )
        return

    active_bytes = bucket.get("active_bytes", 0) or 0
    deleted_bytes = bucket.get("deleted_bytes", 0) or 0
    total_bytes = active_bytes + deleted_bytes

    summary = (
        f"Utilization: {render.disksize(total_bytes)} "
        f"(Active: {render.disksize(active_bytes)}, Deleted: {render.disksize(deleted_bytes)})"
    )

    region = bucket.get("region")
    if region:
        summary += f", region: {region}"

    yield Result(state=State.OK, summary=summary)
    yield Metric("wasabi_active_bytes", active_bytes)
    yield Metric("wasabi_deleted_bytes", deleted_bytes)
    yield Metric("wasabi_total_bytes", total_bytes)


agent_section_wasabi_bucket_utilization = AgentSection(
    name="wasabi_bucket_utilization",
    parse_function=parse_wasabi_bucket_utilization,
)

check_plugin_wasabi_bucket_utilization = CheckPlugin(
    name="wasabi_bucket_utilization",
    service_name="Wasabi Bucket %s",
    discovery_function=discover_wasabi_bucket_utilization,
    check_function=check_wasabi_bucket_utilization,
)
