import os
import time
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError


dynamodb = boto3.resource("dynamodb")
STATE_TABLE_NAME = os.getenv("MESSAGE_STATE_TABLE")
STATE_TTL_DAYS = int(os.getenv("MESSAGE_STATE_TTL_DAYS", "30"))

CLAIM_ACQUIRED = "ACQUIRED"
CLAIM_BUSY = "BUSY"
CLAIM_COMPLETED = "COMPLETED"
CLAIM_DELIVERED = "DELIVERED"
CLAIM_EXHAUSTED = "EXHAUSTED"


class ClaimOwnershipError(RuntimeError):
    """Raised when a stale or foreign claim token attempts a state transition."""


def _table():
    if not STATE_TABLE_NAME:
        raise RuntimeError(
            "MESSAGE_STATE_TABLE must identify the message-state table."
        )
    return dynamodb.Table(STATE_TABLE_NAME)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def epoch_now() -> int:
    return int(time.time())


def _is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def _claim_state(correlation_id: str) -> dict:
    response = _table().get_item(
        Key={"correlationId": correlation_id},
        ConsistentRead=True,
    )
    return response.get("Item", {})


def create_message_state(canonical_event: dict) -> None:
    correlation = canonical_event["correlation"]
    now = datetime.now(timezone.utc)

    _table().put_item(
        Item={
            "correlationId": correlation["correlationId"],
            "requestEventId": canonical_event["eventId"],
            "eventType": canonical_event["eventType"],
            "partnerId": correlation["partnerId"],
            "processingStatus": "RECEIVED",
            "deliveryStatus": "PENDING",
            "deliveryAttemptCount": 0,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
            "expiresAt": int((now + timedelta(days=STATE_TTL_DAYS)).timestamp()),
        },
        ConditionExpression="attribute_not_exists(correlationId)",
    )


def claim_processing(
    correlation_id: str,
    request_event_id: str,
    claim_token: str,
    lease_seconds: int,
    *,
    now_epoch: int | None = None,
) -> str:
    """Atomically claim processing or classify the failed claim."""

    now_epoch = epoch_now() if now_epoch is None else now_epoch
    try:
        _table().update_item(
            Key={"correlationId": correlation_id},
            UpdateExpression=(
                "SET processingStatus = :processing, "
                "processingClaimToken = :token, "
                "processingClaimExpiresAt = :expires, updatedAt = :updated"
            ),
            ConditionExpression=(
                "attribute_exists(correlationId) AND requestEventId = :eventId "
                "AND processingStatus <> :completed AND "
                "(attribute_not_exists(processingClaimExpiresAt) "
                "OR processingClaimExpiresAt <= :now)"
            ),
            ExpressionAttributeValues={
                ":processing": "PROCESSING",
                ":completed": "COMPLETED",
                ":eventId": request_event_id,
                ":token": claim_token,
                ":expires": now_epoch + lease_seconds,
                ":now": now_epoch,
                ":updated": utc_now(),
            },
        )
        return CLAIM_ACQUIRED
    except ClientError as error:
        if not _is_conditional_failure(error):
            raise
        item = _claim_state(correlation_id)
        if (
            item.get("requestEventId") == request_event_id
            and item.get("processingStatus") == "COMPLETED"
        ):
            return CLAIM_COMPLETED
        return CLAIM_BUSY


def complete_processing(
    correlation_id: str,
    claim_token: str,
    status_message: str,
    response_event_id: str,
) -> None:
    try:
        _table().update_item(
            Key={"correlationId": correlation_id},
            UpdateExpression=(
                "SET processingStatus = :completed, processingMessage = :message, "
                "responseEventId = :responseEventId, updatedAt = :updated "
                "REMOVE processingClaimToken, processingClaimExpiresAt"
            ),
            ConditionExpression=(
                "processingStatus = :processing AND processingClaimToken = :token"
            ),
            ExpressionAttributeValues={
                ":processing": "PROCESSING",
                ":completed": "COMPLETED",
                ":token": claim_token,
                ":message": status_message,
                ":responseEventId": response_event_id,
                ":updated": utc_now(),
            },
        )
    except ClientError as error:
        if _is_conditional_failure(error):
            raise ClaimOwnershipError(
                "Only the active processing claim owner may complete processing."
            ) from error
        raise


def fail_processing(
    correlation_id: str,
    claim_token: str,
    message: str,
) -> None:
    try:
        _table().update_item(
            Key={"correlationId": correlation_id},
            UpdateExpression=(
                "SET processingStatus = :failed, processingMessage = :message, "
                "updatedAt = :updated "
                "REMOVE processingClaimToken, processingClaimExpiresAt"
            ),
            ConditionExpression=(
                "processingStatus = :processing AND processingClaimToken = :token"
            ),
            ExpressionAttributeValues={
                ":processing": "PROCESSING",
                ":failed": "PROCESSING_FAILED",
                ":token": claim_token,
                ":message": message,
                ":updated": utc_now(),
            },
        )
    except ClientError as error:
        if _is_conditional_failure(error):
            raise ClaimOwnershipError(
                "Only the active processing claim owner may fail processing."
            ) from error
        raise


def claim_delivery(
    correlation_id: str,
    delivery_id: str,
    claim_token: str,
    lease_seconds: int,
    max_attempts: int,
    *,
    now_epoch: int | None = None,
) -> dict:
    """Atomically claim one outbound attempt and increment its attempt count."""

    now_epoch = epoch_now() if now_epoch is None else now_epoch
    try:
        response = _table().update_item(
            Key={"correlationId": correlation_id},
            UpdateExpression=(
                "SET deliveryStatus = :delivering, deliveryId = :deliveryId, "
                "deliveryClaimToken = :token, deliveryClaimExpiresAt = :expires, "
                "updatedAt = :updated ADD deliveryAttemptCount :one"
            ),
            ConditionExpression=(
                "attribute_exists(correlationId) AND "
                "(attribute_not_exists(deliveryId) OR deliveryId = :deliveryId) "
                "AND deliveryStatus <> :delivered AND "
                "(attribute_not_exists(deliveryClaimExpiresAt) "
                "OR deliveryClaimExpiresAt <= :now) AND "
                "deliveryAttemptCount < :maxAttempts"
            ),
            ExpressionAttributeValues={
                ":delivering": "DELIVERING",
                ":delivered": "DELIVERED",
                ":deliveryId": delivery_id,
                ":token": claim_token,
                ":expires": now_epoch + lease_seconds,
                ":now": now_epoch,
                ":updated": utc_now(),
                ":one": 1,
                ":maxAttempts": max_attempts,
            },
            ReturnValues="UPDATED_NEW",
        )
        attempt = int(response["Attributes"]["deliveryAttemptCount"])
        return {"status": CLAIM_ACQUIRED, "attempt": attempt}
    except ClientError as error:
        if not _is_conditional_failure(error):
            raise
        item = _claim_state(correlation_id)
        if (
            item.get("deliveryId") == delivery_id
            and item.get("deliveryStatus") == "DELIVERED"
        ):
            return {"status": CLAIM_DELIVERED, "attempt": None}
        if (
            item.get("deliveryId") in (None, delivery_id)
            and int(item.get("deliveryAttemptCount", 0)) >= max_attempts
        ):
            return {"status": CLAIM_EXHAUSTED, "attempt": None}
        return {"status": CLAIM_BUSY, "attempt": None}


def complete_delivery(
    correlation_id: str,
    delivery_id: str,
    claim_token: str,
    message: str,
    destination_status_code: int | None = None,
) -> None:
    expression = (
        "SET deliveryStatus = :delivered, deliveryMessage = :message, "
        "updatedAt = :updated"
    )
    values = {
        ":delivering": "DELIVERING",
        ":delivered": "DELIVERED",
        ":deliveryId": delivery_id,
        ":token": claim_token,
        ":message": message,
        ":updated": utc_now(),
    }
    if destination_status_code is not None:
        expression += ", destinationStatusCode = :code"
        values[":code"] = destination_status_code
    expression += " REMOVE deliveryClaimToken, deliveryClaimExpiresAt"

    _owned_delivery_update(correlation_id, expression, values)


def fail_delivery(
    correlation_id: str,
    delivery_id: str,
    claim_token: str,
    status: str,
    message: str,
) -> None:
    _owned_delivery_update(
        correlation_id,
        (
            "SET deliveryStatus = :status, deliveryMessage = :message, "
            "updatedAt = :updated "
            "REMOVE deliveryClaimToken, deliveryClaimExpiresAt"
        ),
        {
            ":delivering": "DELIVERING",
            ":deliveryId": delivery_id,
            ":token": claim_token,
            ":status": status,
            ":message": message,
            ":updated": utc_now(),
        },
    )


def _owned_delivery_update(
    correlation_id: str,
    update_expression: str,
    values: dict,
) -> None:
    try:
        _table().update_item(
            Key={"correlationId": correlation_id},
            UpdateExpression=update_expression,
            ConditionExpression=(
                "deliveryStatus = :delivering AND deliveryId = :deliveryId "
                "AND deliveryClaimToken = :token"
            ),
            ExpressionAttributeValues=values,
        )
    except ClientError as error:
        if _is_conditional_failure(error):
            raise ClaimOwnershipError(
                "Only the active delivery claim owner may update delivery."
            ) from error
        raise
