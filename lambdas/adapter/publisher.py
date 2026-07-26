import json
import os

import boto3

events = boto3.client("events")

EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME")
EVENT_SOURCE = "legacy.logistics.adapter"


def publish_event(event: dict) -> dict:
    """
    Publish the canonical event to Amazon EventBridge.
    """

    if not EVENT_BUS_NAME:
        raise RuntimeError(
            "EVENT_BUS_NAME must identify the integration event bus."
        )

    response = events.put_events(
        Entries=[
            {
                "Source": EVENT_SOURCE,
                "DetailType": event["eventType"],
                "Detail": json.dumps(event),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    failed = response.get("FailedEntryCount", 0)

    if failed > 0:
        raise RuntimeError(
            f"Failed to publish {failed} event(s) to EventBridge."
        )

    return response
