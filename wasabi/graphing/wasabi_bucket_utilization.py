#!/usr/bin/env python3
"""Metric, graph and perfometer definitions for Wasabi bucket utilization."""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, Unit
from cmk.graphing.v1.perfometers import Closed, FocusRange, Open, Perfometer

UNIT_BYTES = Unit(IECNotation("B"))

metric_wasabi_active_bytes = Metric(
    name="wasabi_active_bytes",
    title=Title("Active storage"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_wasabi_deleted_bytes = Metric(
    name="wasabi_deleted_bytes",
    title=Title("Deleted storage"),
    unit=UNIT_BYTES,
    color=Color.ORANGE,
)

metric_wasabi_total_bytes = Metric(
    name="wasabi_total_bytes",
    title=Title("Total billable storage"),
    unit=UNIT_BYTES,
    color=Color.DARK_GREEN,
)

graph_wasabi_bucket_utilization = Graph(
    name="wasabi_bucket_utilization",
    title=Title("Wasabi bucket utilization"),
    minimal_range=MinimalRange(0, 1024**3),
    compound_lines=[
        "wasabi_active_bytes",
        "wasabi_deleted_bytes",
    ],
)

perfometer_wasabi_bucket_utilization = Perfometer(
    name="wasabi_bucket_utilization",
    focus_range=FocusRange(Closed(0), Open(1024**4)),
    segments=["wasabi_active_bytes", "wasabi_deleted_bytes"],
)
