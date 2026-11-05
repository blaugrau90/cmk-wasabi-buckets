#!/usr/bin/env python3
"""Server-side calls for the Wasabi Storage Utilization special agent."""

from collections.abc import Iterator

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class Params(BaseModel):
    access_key: str
    secret_key: Secret
    base_url: str = "https://stats.wasabisys.com"
    lookback_days: int = 30


def _agent_arguments(
    params: Params, host_config: HostConfig
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--access-key", params.access_key,
        "--secret-key", params.secret_key.unsafe("%s"),
        "--base-url", params.base_url,
        "--lookback-days", str(params.lookback_days),
    ]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_wasabi = SpecialAgentConfig(
    name="wasabi",
    parameter_parser=Params.model_validate,
    commands_function=_agent_arguments,
)
