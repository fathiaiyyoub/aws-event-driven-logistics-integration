from datetime import datetime, timezone
import uuid


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
        "eventId": str(uuid.uuid4()),
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
