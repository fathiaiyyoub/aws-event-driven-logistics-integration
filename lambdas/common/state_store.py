import os
from datetime import datetime, timedelta, timezone

import boto3


dynamodb = boto3.resource("dynamodb")
STATE_TABLE_NAME = os.getenv("MESSAGE_STATE_TABLE")
STATE_TTL_DAYS = int(os.getenv("MESSAGE_STATE_TTL_DAYS", "30"))


def _table():
    if not STATE_TABLE_NAME:
        raise RuntimeError(
            "MESSAGE_STATE_TABLE must identify the message-state table."
        )
    return dynamodb.Table(STATE_TABLE_NAME)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def update_processing_status(correlation_id: str, status: str, message: str | None = None) -> None:
    expression = "SET processingStatus = :status, updatedAt = :updated"
    values = {":status": status, ":updated": utc_now()}

    if message is not None:
        expression += ", processingMessage = :message"
        values[":message"] = message

    _table().update_item(
        Key={"correlationId": correlation_id},
        UpdateExpression=expression,
        ExpressionAttributeValues=values,
    )


def mark_delivery_attempt(correlation_id: str) -> int:
    response = _table().update_item(
        Key={"correlationId": correlation_id},
        UpdateExpression=(
            "SET deliveryStatus = :status, updatedAt = :updated "
            "ADD deliveryAttemptCount :one"
        ),
        ExpressionAttributeValues={
            ":status": "RETRYING",
            ":updated": utc_now(),
            ":one": 1,
        },
        ReturnValues="UPDATED_NEW",
    )
    return int(response["Attributes"]["deliveryAttemptCount"])


def update_delivery_status(
    correlation_id: str,
    status: str,
    *,
    message: str | None = None,
    destination_status_code: int | None = None,
) -> None:
    expression = "SET deliveryStatus = :status, updatedAt = :updated"
    values = {":status": status, ":updated": utc_now()}

    if message is not None:
        expression += ", deliveryMessage = :message"
        values[":message"] = message

    if destination_status_code is not None:
        expression += ", destinationStatusCode = :code"
        values[":code"] = destination_status_code

    _table().update_item(
        Key={"correlationId": correlation_id},
        UpdateExpression=expression,
        ExpressionAttributeValues=values,
    )
