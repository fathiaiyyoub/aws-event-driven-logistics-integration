import uuid
from datetime import datetime, timezone


def get_correlation_metadata(message: dict) -> dict:
    """Build durable routing metadata without embedding endpoint URLs or secrets."""

    correlation_id = message.get("correlationId") or str(uuid.uuid4())
    # Proxy requests carry identity either in business fields or in metadata
    # normalised by the Adapter (for example X-Partner-Id on retrieval).
    partner_id = (
        message.get("partnerId")
        or message.get("sourceSystem")
        or message.get("eventSource")
    )

    if not partner_id:
        raise ValueError("A partnerId, sourceSystem, or eventSource is required.")

    return {
        "correlationId": correlation_id,
        "partnerId": partner_id,
        "sourceSystem": message.get("sourceSystem") or message.get("eventSource") or partner_id,
        "originalFormat": message.get("messageFormat", "JSON").upper(),
        "receivedAt": datetime.now(timezone.utc).isoformat(),
    }
