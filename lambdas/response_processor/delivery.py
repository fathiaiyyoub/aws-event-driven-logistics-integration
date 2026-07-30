from urllib import error, parse, request

from lambdas.adapter.serializer import serialize_response
from .errors import (
    DeliveryError,
    PartnerConfigurationError,
    UnsupportedDeliveryMethodError,
)
from .secrets_extension import get_secret


MIN_TIMEOUT_SECONDS = 1
# Leave runtime headroom inside the 60-second Response Lambda timeout for
# configuration, secret retrieval, state transitions, and logging.
MAX_TIMEOUT_SECONDS = 50
SUPPORTED_MESSAGE_FORMATS = {"JSON", "XML"}


def _deliver_https(
    response_event: dict,
    config: dict,
    idempotency_key: str,
) -> dict:
    credentials = get_secret(config.get("secretId"))
    payload = serialize_response(
        response_event,
        config["messageFormat"],
    ).encode("utf-8")

    headers = {
        "Content-Type": (
            "application/xml"
            if config["messageFormat"] == "XML"
            else "application/json"
        ),
        "User-Agent": "aws-logistics-integration-platform",
        "Idempotency-Key": idempotency_key,
    }
    if credentials.get("authorizationHeader"):
        headers["Authorization"] = credentials["authorizationHeader"]
    if credentials.get("apiKey"):
        headers["x-api-key"] = credentials["apiKey"]

    outbound_request = request.Request(
        config["endpointUrl"],
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(
            outbound_request,
            timeout=config["timeoutSeconds"],
        ) as response:
            status_code = response.getcode()
    except error.HTTPError as exc:
        raise DeliveryError(f"Destination returned HTTP {exc.code}.") from exc
    except error.URLError as exc:
        raise DeliveryError("Destination connection failed.") from exc

    if status_code < 200 or status_code >= 300:
        raise DeliveryError(
            f"Destination returned unexpected HTTP {status_code}."
        )

    return {"statusCode": status_code}


# This is the single source of truth for runtime-supported delivery methods.
# Adding a future mechanism requires a handler plus its IAM, infrastructure,
# configuration validation, and tests.
DELIVERY_HANDLERS = {
    "HTTPS_WEBHOOK": _deliver_https,
    "PRIVATE_HTTPS": _deliver_https,
}


def _required_string(config: dict, field_name: str) -> str:
    value = config.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise PartnerConfigurationError(
            f"{field_name} must be a non-empty string."
        )
    return value.strip()


def _normalize_timeout(value) -> int:
    if isinstance(value, bool):
        raise PartnerConfigurationError(
            "timeoutSeconds must be a positive integer."
        )
    try:
        timeout = int(value)
    except (TypeError, ValueError) as exc:
        raise PartnerConfigurationError(
            "timeoutSeconds must be a positive integer."
        ) from exc

    if timeout < MIN_TIMEOUT_SECONDS or timeout > MAX_TIMEOUT_SECONDS:
        raise PartnerConfigurationError(
            f"timeoutSeconds must be between {MIN_TIMEOUT_SECONDS} "
            f"and {MAX_TIMEOUT_SECONDS}."
        )
    return timeout


def normalize_delivery_configuration(config: dict) -> dict:
    """Validate DynamoDB configuration and return one normalized contract."""

    if not isinstance(config, dict):
        raise PartnerConfigurationError(
            "Partner configuration must be an object."
        )

    partner_id = _required_string(config, "partnerId")
    enabled = config.get("enabled", False)
    if not isinstance(enabled, bool):
        raise PartnerConfigurationError("enabled must be a boolean.")
    if not enabled:
        raise PartnerConfigurationError(
            f"Partner {partner_id} is disabled."
        )

    delivery_method = _required_string(config, "deliveryMethod").upper()
    if delivery_method not in DELIVERY_HANDLERS:
        supported = ", ".join(sorted(DELIVERY_HANDLERS))
        raise UnsupportedDeliveryMethodError(
            f"Unsupported delivery method '{delivery_method}'. "
            f"Supported methods: {supported}."
        )

    endpoint_url = _required_string(config, "endpointUrl")
    parsed_url = parse.urlsplit(endpoint_url)
    if parsed_url.scheme.lower() != "https" or not parsed_url.netloc:
        raise PartnerConfigurationError(
            "endpointUrl must be a valid https:// URL."
        )

    message_format = config.get("messageFormat", "JSON")
    if not isinstance(message_format, str):
        raise PartnerConfigurationError(
            "messageFormat must be JSON or XML."
        )
    message_format = message_format.strip().upper()
    if message_format not in SUPPORTED_MESSAGE_FORMATS:
        raise PartnerConfigurationError(
            "messageFormat must be JSON or XML."
        )

    secret_id = config.get("secretId")
    if secret_id is not None:
        if not isinstance(secret_id, str) or not secret_id.strip():
            raise PartnerConfigurationError(
                "secretId must be a non-empty string when provided."
            )
        secret_id = secret_id.strip()

    return {
        "partnerId": partner_id,
        "enabled": True,
        "deliveryMethod": delivery_method,
        "endpointUrl": endpoint_url,
        "messageFormat": message_format,
        "secretId": secret_id,
        "timeoutSeconds": _normalize_timeout(
            config.get("timeoutSeconds", 10)
        ),
    }


def deliver_response(
    response_event: dict,
    config: dict,
    idempotency_key: str,
) -> dict:
    """Resolve and execute the registered handler for normalized config."""

    config = normalize_delivery_configuration(config)
    delivery_method = config["deliveryMethod"]
    handler = DELIVERY_HANDLERS.get(delivery_method)
    if handler is None:
        # Defensive check for callers that bypass get_partner_config().
        supported = ", ".join(sorted(DELIVERY_HANDLERS))
        raise UnsupportedDeliveryMethodError(
            f"Unsupported delivery method '{delivery_method}'. "
            f"Supported methods: {supported}."
        )
    return handler(response_event, config, idempotency_key)
