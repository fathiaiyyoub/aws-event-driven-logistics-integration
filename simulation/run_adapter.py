import json
import sys
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lambdas.adapter.lambda_function import lambda_handler


payload_file = (
    Path(__file__).parent.parent
    / "payloads"
    / "partner_a_create_shipment.xml"
)


def mock_publish_event(canonical_event: dict) -> dict:
    """
    Simulate EventBridge publishing during local testing.
    """

    print("\nCanonical Event")
    print(json.dumps(canonical_event, indent=2))

    return {
        "FailedEntryCount": 0,
        "Entries": [
            {
                "EventId": "local-test-event"
            }
        ]
    }


def main() -> None:
    xml_message = payload_file.read_text(encoding="utf-8")

    event = {
        "body": xml_message,
        "headers": {"Content-Type": "application/xml"},
    }

    with patch(
        "lambdas.adapter.lambda_function.publish_event",
        side_effect=mock_publish_event
    ), patch(
        "lambdas.adapter.lambda_function.create_message_state",
    ):
        response = lambda_handler(event, None)

    print("\nAdapter Response")
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
