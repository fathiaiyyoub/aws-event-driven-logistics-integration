from typing import Any

REQUIRED_EVENT_FIELDS = ["eventId", "eventType", "eventSource", "timestamp", "correlation", "payload"]
REQUIRED_CORRELATION_FIELDS = [
    "correlationId",
    "partnerId",
    "sourceSystem",
    "originalFormat",
    "receivedAt",
]
SUPPORTED_EVENT_TYPES = {"CreateShipment", "UpdateShipmentStatus", "RetrieveShipment"}


def validate_event(event: Any) -> tuple[bool, str]:
    if not isinstance(event, dict):
        return False, "The event must be a JSON object."

    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in event or event[field] is None]
    if missing:
        return False, "Missing required event fields: " + ", ".join(missing)

    if not isinstance(event["correlation"], dict):
        return False, "The correlation field must be a JSON object."

    missing = [field for field in REQUIRED_CORRELATION_FIELDS if not event["correlation"].get(field)]
    if missing:
        return False, "Missing required correlation fields: " + ", ".join(missing)

    if not isinstance(event["payload"], dict):
        return False, "The payload field must be a JSON object."

    if event["eventType"] not in SUPPORTED_EVENT_TYPES:
        return False, f"Unsupported event type: {event['eventType']}."

    return True, ""
