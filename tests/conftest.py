"""Test infrastructure for the Wasabi Checkmk plugin.

The real `cmk.agent_based.v2` module only exists inside a Checkmk site's
Python environment. To unit-test the check plugin logic without a full
Checkmk installation, a minimal stand-in module is registered in
`sys.modules` before the plugin module is imported. It reproduces just the
runtime surface the plugin actually uses (classes/enums/render helper) -
it is not a general Checkmk API stub.
"""

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent


def _install_fake_cmk_agent_based_v2() -> None:
    try:
        import cmk.agent_based.v2  # noqa: F401

        return  # real module is available (running inside a Checkmk site) - use it
    except ImportError:
        pass

    class State(Enum):
        OK = 0
        WARN = 1
        CRIT = 2
        UNKNOWN = 3

    @dataclass
    class Result:
        state: "State"
        summary: str | None = None
        notice: str | None = None

    @dataclass
    class Service:
        item: str | None = None

    @dataclass
    class Metric:
        name: str
        value: float
        levels: Any = None
        boundaries: Any = None

    @dataclass
    class AgentSection:
        name: str
        parse_function: Any
        parsed_section_name: str | None = None

    @dataclass
    class CheckPlugin:
        name: str
        service_name: str
        discovery_function: Any
        check_function: Any
        check_default_parameters: dict = field(default_factory=dict)
        check_ruleset_name: str | None = None

    def _disksize(bytes_: float) -> str:
        value = float(bytes_)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
            if abs(value) < 1024.0:
                return f"{value:.2f} {unit}" if unit != "B" else f"{value:.0f} B"
            value /= 1024.0
        return f"{value:.2f} EiB"

    class _Render:
        disksize = staticmethod(_disksize)

    StringTable = list
    CheckResult = Iterable
    DiscoveryResult = Iterable

    v2 = ModuleType("cmk.agent_based.v2")
    v2.State = State
    v2.Result = Result
    v2.Service = Service
    v2.Metric = Metric
    v2.AgentSection = AgentSection
    v2.CheckPlugin = CheckPlugin
    v2.render = _Render()
    v2.StringTable = StringTable
    v2.CheckResult = CheckResult
    v2.DiscoveryResult = DiscoveryResult

    agent_based_pkg = ModuleType("cmk.agent_based")
    agent_based_pkg.v2 = v2
    cmk_pkg = ModuleType("cmk")
    cmk_pkg.agent_based = agent_based_pkg

    sys.modules.setdefault("cmk", cmk_pkg)
    sys.modules["cmk.agent_based"] = agent_based_pkg
    sys.modules["cmk.agent_based.v2"] = v2


_install_fake_cmk_agent_based_v2()


def load_module(relative_path: str, module_name: str) -> ModuleType:
    """Load a plugin file (which may have no .py extension) as a module by path."""
    path = REPO_ROOT / relative_path
    loader = SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_loader(module_name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module
