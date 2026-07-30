from datetime import datetime, timezone
import uuid


RESPONSE_ID_NAMESPACE = uuid.UUID("c8c96c7a-f15f-4b62-8df6-78de506f5781")


def build_response_event(
    original_event: dict,
    processing_result: dict
) -> dict:
    """
    Build the internal response event published after worker processing.

    The original correlation metadata is preserved so the outbound
    Adapter can deliver the response to the correct originating system.
    """

    correlation = original_event["correlation"]

    return {
        # Stable across SQS retries so the response consumer can suppress a
        # physically duplicated EventBridge publication atomically.
        "eventId": str(
            uuid.uuid5(RESPONSE_ID_NAMESPACE, original_event["eventId"])
        ),
        "eventType": "ProcessingResponse",
        "eventSource": "legacy.logistics.worker",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation": correlation,
        "requestEventId": original_event["eventId"],
        "requestEventType": original_event["eventType"],
        "status": processing_result["status"],
        "message": processing_result["message"],
        "payload": {
            key: value
            for key, value in processing_result.items()
            if key not in {"status", "message"}
        }
    }
