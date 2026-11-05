#!/usr/bin/env python3
"""Ruleset for the Wasabi Storage Utilization special agent."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Password,
    String,
    migrate_to_password,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate_remove_lookback(value: object) -> dict:
    """Drop the 'lookback_days' option of versions <= 1.1.0 from existing rules."""
    if not isinstance(value, dict):
        raise TypeError(value)
    return {k: v for k, v in value.items() if k != "lookback_days"}


def _special_agent_formspec() -> Dictionary:
    return Dictionary(
        migrate=_migrate_remove_lookback,
        title=Title("Wasabi Storage Utilization"),
        help_text=Help(
            "Connect to the Wasabi Stats API to monitor the storage utilization of all "
            "buckets in a Wasabi account. Buckets are discovered automatically from the "
            "API response - no bucket names need to be configured here. Requires a Wasabi "
            "root API key or a key with billing permission (WAC API keys do not work)."
        ),
        elements={
            "access_key": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Wasabi Access Key"),
                    help_text=Help(
                        "The Access Key ID of a Wasabi root API key or a key with billing "
                        "permission (WAC API keys do not work)."
                    ),
                ),
            ),
            "secret_key": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Wasabi Secret Key"),
                    help_text=Help(
                        "The Secret Key belonging to the Access Key above. Access Key and "
                        "Secret Key are combined into the 'Authorization: <AccessKey>:"
                        "<SecretKey>' header expected by the Wasabi Stats API."
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "base_url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Stats API base URL"),
                    help_text=Help(
                        "Base URL of the Wasabi Stats API. Only change this for special "
                        "setups, e.g. a different Wasabi region endpoint."
                    ),
                    prefill=DefaultValue("https://stats.wasabisys.com"),
                ),
            ),
        },
    )


rule_spec_wasabi_agent = SpecialAgent(
    topic=Topic.CLOUD,
    name="wasabi",
    title=Title("Wasabi Storage Utilization"),
    parameter_form=_special_agent_formspec,
)
