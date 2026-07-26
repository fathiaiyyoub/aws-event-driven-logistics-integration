import json
import os

from .config_store import get_partner_config
from .delivery import deliver_response
from .errors import (
    DeliveryError,
    PartnerConfigurationError,
    ResponseMessageError,
)
from .secrets_extension import CredentialRetrievalError
from lambdas.common.state_store import (
    mark_delivery_attempt,
    update_delivery_status,
)


MAX_DELIVERY_ATTEMPTS = int(os.getenv("MAX_DELIVERY_ATTEMPTS", "3"))


def _log(message, *, message_id, category, correlation_id=None,
         partner_id=None, attempt=None):
    """Write structured operational context without bodies or credentials."""

    print(json.dumps({
        "message": message,
        "messageId": message_id,
        "correlationId": correlation_id,
        "partnerId": partner_id,
        "attempt": attempt,
        "errorCategory": category,
    }))


def _parse_response_record(record):
    try:
        message = json.loads(record["body"])
        response_event = message.get("detail", message)
        correlation = response_event["correlation"]
        correlation_id = correlation["correlationId"]
        partner_id = correlation["partnerId"]
    except (
        AttributeError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        raise ResponseMessageError(
            "The response queue message does not match the required contract."
        ) from exc

    if not isinstance(correlation_id, str) or not correlation_id.strip():
        raise ResponseMessageError("correlationId must be a non-empty string.")
    if not isinstance(partner_id, str) or not partner_id.strip():
        raise ResponseMessageError("partnerId must be a non-empty string.")

    return response_event, correlation_id.strip(), partner_id.strip()


def _safe_state_update(correlation_id, status, message):
    if not correlation_id:
        return
    try:
        update_delivery_status(
            correlation_id,
            status,
            message=message,
        )
    except Exception:
        # A state-write failure must not hide the original delivery outcome.
        pass


def lambda_handler(event, context):
    """Deliver outbound responses and return partial SQS batch failures."""

    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        correlation_id = None
        partner_id = None
        attempt = None

        try:
            response_event, correlation_id, partner_id = (
                _parse_response_record(record)
            )

            # Configuration defects are resolved before counting a real
            # outbound network-delivery attempt.
            config = get_partner_config(partner_id)

        except PartnerConfigurationError as exc:
            safe_message = str(exc)
            _safe_state_update(
                correlation_id,
                "CONFIGURATION_FAILED",
                safe_message,
            )
            _log(
                safe_message,
                message_id=message_id,
                correlation_id=correlation_id,
                partner_id=partner_id,
                category=type(exc).__name__,
            )
            # Preserve the record through normal SQS retry/DLQ handling without
            # counting a network attempt. It can be redriven after correction.
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        except ResponseMessageError as exc:
            _log(
                str(exc),
                message_id=message_id,
                correlation_id=correlation_id,
                partner_id=partner_id,
                category="INVALID_RESPONSE_MESSAGE",
            )
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        try:
            attempt = mark_delivery_attempt(correlation_id)
            result = deliver_response(response_event, config)

            update_delivery_status(
                correlation_id,
                "DELIVERED",
                message=(
                    f"Delivered using {config['deliveryMethod']} "
                    f"on attempt {attempt}."
                ),
                destination_status_code=result.get("statusCode"),
            )
            _log(
                "Response delivered successfully.",
                message_id=message_id,
                correlation_id=correlation_id,
                partner_id=partner_id,
                attempt=attempt,
                category=None,
            )

        except (DeliveryError, CredentialRetrievalError) as exc:
            terminal = (
                attempt is not None
                and attempt >= MAX_DELIVERY_ATTEMPTS
            )
            status = "DELIVERY_FAILED" if terminal else "RETRYING"
            category = (
                "CREDENTIAL_RETRIEVAL_FAILED"
                if isinstance(exc, CredentialRetrievalError)
                else "OUTBOUND_DELIVERY_FAILED"
            )
            safe_message = (
                "Outbound delivery failed after the maximum attempts."
                if terminal
                else "Outbound delivery failed and will be retried."
            )
            _safe_state_update(correlation_id, status, safe_message)
            _log(
                safe_message,
                message_id=message_id,
                correlation_id=correlation_id,
                partner_id=partner_id,
                attempt=attempt,
                category=category,
            )
            batch_item_failures.append({"itemIdentifier": message_id})

        except Exception:
            safe_message = "Unexpected outbound delivery failure."
            _safe_state_update(
                correlation_id,
                "DELIVERY_FAILED",
                safe_message,
            )
            _log(
                safe_message,
                message_id=message_id,
                correlation_id=correlation_id,
                partner_id=partner_id,
                attempt=attempt,
                category="INTERNAL_DELIVERY_ERROR",
            )
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
