import json
import os
import uuid

import boto3

from .validator import validate_event
from .processor import process_event
from .response import build_response_event
from lambdas.common.state_store import (
    CLAIM_ACQUIRED,
    CLAIM_COMPLETED,
    ClaimOwnershipError,
    claim_processing,
    complete_processing,
    fail_processing,
)


events = boto3.client("events")
EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME")
EVENT_SOURCE = "legacy.logistics.worker"
PROCESSING_LEASE_SECONDS = int(os.getenv("PROCESSING_LEASE_SECONDS", "120"))


def lambda_handler(event, context):
    """Process SQS records and return partial batch failures for retry/DLQ handling."""

    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        correlation_id = None
        claim_token = str(uuid.uuid4())
        claim_acquired = False

        try:
            message = json.loads(record["body"])
            canonical_event = message.get("detail", message)
            correlation_id = canonical_event["correlation"]["correlationId"]
            request_event_id = canonical_event["eventId"]

            claim_status = claim_processing(
                correlation_id,
                request_event_id,
                claim_token,
                PROCESSING_LEASE_SECONDS,
            )
            if claim_status == CLAIM_COMPLETED:
                continue
            if claim_status != CLAIM_ACQUIRED:
                batch_item_failures.append({"itemIdentifier": message_id})
                continue
            claim_acquired = True

            valid, reason = validate_event(canonical_event)
            if not valid:
                processing_result = {
                    "status": "VALIDATION_FAILED",
                    "message": reason,
                }
            else:
                processing_result = process_event(canonical_event)

            response_event = build_response_event(
                canonical_event,
                processing_result,
            )

            # Publication intentionally precedes COMPLETED. A crash between
            # these operations can republish the deterministic response ID,
            # but cannot lose the response through premature acknowledgement.
            publish_response(response_event)
            complete_processing(
                correlation_id,
                claim_token,
                processing_result["message"],
                response_event["eventId"],
            )

        except Exception as exc:
            if claim_acquired and correlation_id:
                try:
                    fail_processing(correlation_id, claim_token, str(exc))
                except ClaimOwnershipError:
                    pass
                except Exception:
                    pass

            print(json.dumps({
                "message": "Worker processing failed.",
                "messageId": message_id,
                "error": str(exc),
            }))
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
