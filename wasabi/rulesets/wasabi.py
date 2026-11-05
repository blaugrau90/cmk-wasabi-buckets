#!/usr/bin/env python3
"""Ruleset for the Wasabi Storage Utilization special agent."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    Password,
    String,
    migrate_to_password,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _special_agent_formspec() -> Dictionary:
    return Dictionary(
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
            "lookback_days": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Lookback period (days)"),
                    help_text=Help(
                        "Number of days before today to use as the 'from' date when "
                        "querying the utilization API. The agent always uses the most "
                        "recent record per bucket within this window, so this only needs "
                        "to be large enough to reliably contain at least one data point "
                        "per bucket. Wasabi's daily utilization snapshots can lag by "
                        "several days before they appear in the Stats API, so a short "
                        "window (e.g. 2 days) may return no data at all - 30 days is a "
                        "safe default."
                    ),
                    prefill=DefaultValue(30),
                    custom_validate=(validators.NumberInRange(min_value=1, max_value=90),),
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
