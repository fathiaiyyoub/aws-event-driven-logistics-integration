import json
import sys
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lambdas.worker.lambda_function import lambda_handler


def mock_publish_response(response_event: dict):
    """
    Simulate publishing the processing result to EventBridge.
    """

    print("\nResponse Event")
    print(json.dumps(response_event, indent=2))


def main():

    canonical_event = {
        "eventId": "evt-1001",
        "eventType": "CreateShipment",
        "eventSource": "partner.dhl",
        "timestamp": "2026-01-01T10:00:00Z",
        "correlation": {
            "correlationId": "corr-1001",
            "partnerId": "DHL",
            "sourceSystem": "partner.dhl",
            "originalFormat": "JSON",
            "receivedAt": "2026-01-01T10:00:00Z"
        },
        "payload": {
            "shipmentId": "SHIP-1001"
        }
    }

    sqs_event = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "detail": canonical_event
                    }
                )
            }
        ]
    }

    with patch(
        "lambdas.worker.lambda_function.publish_response",
        side_effect=mock_publish_response
    ), patch(
        "lambdas.worker.lambda_function.update_processing_status",
    ):

        response = lambda_handler(
            sqs_event,
            None
        )

    print("\nWorker Result")
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
