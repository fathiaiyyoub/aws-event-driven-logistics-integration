import json
import os
import uuid

from .config_store import get_partner_config
from .delivery import deliver_response
from .errors import (
    DeliveryError,
    PartnerConfigurationError,
    ResponseMessageError,
)
from .secrets_extension import CredentialRetrievalError
from lambdas.common.state_store import (
    CLAIM_ACQUIRED,
    CLAIM_DELIVERED,
    CLAIM_EXHAUSTED,
    ClaimOwnershipError,
    claim_delivery,
    complete_delivery,
    fail_delivery,
)


MAX_DELIVERY_ATTEMPTS = int(os.getenv("MAX_DELIVERY_ATTEMPTS", "3"))
DELIVERY_LEASE_SECONDS = int(os.getenv("DELIVERY_LEASE_SECONDS", "120"))


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
        delivery_id = response_event["eventId"]
    except (
        AttributeError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        raise ResponseMessageError(
            "The response queue message does not match the required contract."
        ) from exc

    for name, value in (
        ("correlationId", correlation_id),
        ("partnerId", partner_id),
        ("eventId", delivery_id),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ResponseMessageError(f"{name} must be a non-empty string.")

    return (
        response_event,
        correlation_id.strip(),
        partner_id.strip(),
        delivery_id.strip(),
    )


def _owned_failure(
    correlation_id,
    delivery_id,
    claim_token,
    status,
    message,
):
    try:
        fail_delivery(
            correlation_id,
            delivery_id,
            claim_token,
            status,
            message,
        )
    except ClaimOwnershipError:
        pass
    except Exception:
        pass


def lambda_handler(event, context):
    """Deliver outbound responses and return partial SQS batch failures."""

    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        correlation_id = None
        partner_id = None
        delivery_id = None
        attempt = None
        claim_token = str(uuid.uuid4())
        claim_acquired = False

        try:
            (
                response_event,
                correlation_id,
                partner_id,
                delivery_id,
            ) = _parse_response_record(record)
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
            claim = claim_delivery(
                correlation_id,
                delivery_id,
                claim_token,
                DELIVERY_LEASE_SECONDS,
                MAX_DELIVERY_ATTEMPTS,
            )
            if claim["status"] == CLAIM_DELIVERED:
                continue
            if claim["status"] in (CLAIM_EXHAUSTED,):
                _log(
                    "Maximum outbound delivery attempts already exhausted.",
                    message_id=message_id,
                    correlation_id=correlation_id,
                    partner_id=partner_id,
                    category="DELIVERY_ATTEMPTS_EXHAUSTED",
                )
                batch_item_failures.append({"itemIdentifier": message_id})
                continue
            if claim["status"] != CLAIM_ACQUIRED:
                batch_item_failures.append({"itemIdentifier": message_id})
                continue

            claim_acquired = True
            attempt = claim["attempt"]
            config = get_partner_config(partner_id)
            result = deliver_response(
                response_event,
                config,
                delivery_id,
            )

            complete_delivery(
                correlation_id,
                delivery_id,
                claim_token,
                (
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

        except PartnerConfigurationError as exc:
            safe_message = str(exc)
            if claim_acquired:
                _owned_failure(
                    correlation_id,
                    delivery_id,
                    claim_token,
                    "CONFIGURATION_FAILED",
                    safe_message,
                )
            _log(
                safe_message,
                message_id=message_id,
                correlation_id=correlation_id,
                partner_id=partner_id,
                attempt=attempt,
                category=type(exc).__name__,
            )
            batch_item_failures.append({"itemIdentifier": message_id})

        except (DeliveryError, CredentialRetrievalError) as exc:
            terminal = attempt is not None and attempt >= MAX_DELIVERY_ATTEMPTS
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
            if claim_acquired:
                _owned_failure(
                    correlation_id,
                    delivery_id,
                    claim_token,
                    status,
                    safe_message,
                )
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
            if claim_acquired:
                _owned_failure(
                    correlation_id,
                    delivery_id,
                    claim_token,
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
