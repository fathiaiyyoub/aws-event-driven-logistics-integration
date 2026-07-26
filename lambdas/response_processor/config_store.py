import os

import boto3

from .delivery import normalize_delivery_configuration
from .errors import PartnerConfigurationError


dynamodb = boto3.resource("dynamodb")
CONFIG_TABLE_NAME = os.getenv("PARTNER_CONFIG_TABLE")


def get_partner_config(partner_id: str) -> dict:
    if not CONFIG_TABLE_NAME:
        raise PartnerConfigurationError(
            "PARTNER_CONFIG_TABLE must identify the partner-configuration table."
        )

    response = dynamodb.Table(CONFIG_TABLE_NAME).get_item(
        Key={"partnerId": partner_id},
        ConsistentRead=True,
    )
    config = response.get("Item")

    if not config:
        raise PartnerConfigurationError(f"No configuration exists for partner {partner_id}.")

    configured_partner_id = config.get("partnerId")
    if not isinstance(configured_partner_id, str) or not configured_partner_id.strip():
        raise PartnerConfigurationError("partnerId must be a non-empty string.")
    if configured_partner_id != partner_id:
        raise PartnerConfigurationError("The partner configuration key does not match the requested partner.")

    enabled = config.get("enabled", False)
    if not isinstance(enabled, bool):
        raise PartnerConfigurationError("enabled must be a boolean.")
    if not enabled:
        raise PartnerConfigurationError(f"Partner {partner_id} is disabled.")

    return normalize_delivery_configuration(config)
