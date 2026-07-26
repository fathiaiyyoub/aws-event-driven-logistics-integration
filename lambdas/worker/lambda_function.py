import json
import os

import boto3

from .validator import validate_event
from .processor import process_event
from .response import build_response_event
from lambdas.common.state_store import update_processing_status


events = boto3.client("events")
EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME")
EVENT_SOURCE = "legacy.logistics.worker"


def lambda_handler(event, context):
    """Process SQS records and return partial batch failures for retry/DLQ handling."""

    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")

        try:
            message = json.loads(record["body"])
            canonical_event = message.get("detail", message)
            correlation_id = canonical_event["correlation"]["correlationId"]

            update_processing_status(correlation_id, "PROCESSING")
            valid, reason = validate_event(canonical_event)

            if not valid:
                processing_result = {
                    "status": "VALIDATION_FAILED",
                    "message": reason,
                }
            else:
                processing_result = process_event(canonical_event)

            update_processing_status(
                correlation_id,
                processing_result["status"],
                processing_result["message"],
            )
            publish_response(build_response_event(canonical_event, processing_result))

        except Exception as exc:
            try:
                correlation_id = canonical_event.get("correlation", {}).get("correlationId")
                if correlation_id:
                    update_processing_status(correlation_id, "PROCESSING_FAILED", str(exc))
            except Exception:
                pass

            print(json.dumps({"message": "Worker processing failed.", "messageId": message_id, "error": str(exc)}))
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}


def publish_response(response_event: dict):
    if not EVENT_BUS_NAME:
        raise RuntimeError(
            "EVENT_BUS_NAME must identify the integration event bus."
        )

    response = events.put_events(
        Entries=[{
            "Source": EVENT_SOURCE,
            "DetailType": response_event["eventType"],
            "Detail": json.dumps(response_event),
            "EventBusName": EVENT_BUS_NAME,
        }]
    )

    if response.get("FailedEntryCount", 0) > 0:
        raise RuntimeError("Failed to publish response event to EventBridge.")
