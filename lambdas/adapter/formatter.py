from datetime import datetime, timezone
import uuid


def format_canonical_event(message: dict, correlation: dict) -> dict:
    """Convert an inbound message into the platform canonical JSON event."""

    # JSON generally wraps business fields in payload. XML-normalised and
    # legacy direct messages may provide them at the top level.
    payload = message.get("payload")
    if payload is None:
        metadata_fields = {
            "eventId",
            "correlationId",
            "eventType",
            "eventSource",
            "partnerId",
            "sourceSystem",
            "messageFormat",
            "timestamp",
        }
        payload = {
            key: value
            for key, value in message.items()
            if key not in metadata_fields
        }

    return {
        "eventId": str(uuid.uuid4()),
        "eventType": message.get("eventType", "UnknownEvent"),
        "eventSource": correlation["sourceSystem"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation": correlation,
        "payload": payload,
    }
