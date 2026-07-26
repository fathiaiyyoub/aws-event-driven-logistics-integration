import json
import sys
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Running ``python simulation/run_end_to_end.py`` places only the simulation
# directory on sys.path. Add the repository root containing the canonical
# ``lambdas`` source package.
sys.path.insert(0, str(PROJECT_ROOT))

from lambdas.adapter.lambda_function import lambda_handler as adapter_handler
from lambdas.worker.lambda_function import lambda_handler as worker_handler


def main() -> None:
    payload_path = PROJECT_ROOT / "payloads" / "create_shipment.json"
    inbound_payload = json.loads(
        payload_path.read_text(encoding="utf-8")
    )

    captured_canonical_event = {}
    captured_response_event = {}

    def capture_canonical_event(event: dict) -> dict:
        captured_canonical_event.update(event)

        print("\n1. Canonical event published by Adapter")
        print(json.dumps(event, indent=2))

        return {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "local-inbound-event"}],
        }

    def capture_response_event(event: dict) -> None:
        captured_response_event.update(event)

        print("\n2. Response event published by Worker")
        print(json.dumps(event, indent=2))

    api_gateway_event = {
        "body": json.dumps(inbound_payload)
    }

    with patch(
        "lambdas.adapter.lambda_function.publish_event",
        side_effect=capture_canonical_event,
    ), patch(
        "lambdas.adapter.lambda_function.create_message_state",
    ):
        adapter_response = adapter_handler(
            api_gateway_event,
            None,
        )

    print("\nAdapter acknowledgement")
    print(json.dumps(adapter_response, indent=2))

    sqs_event = {
        "Records": [
            {
                "messageId": "local-message-001",
                "body": json.dumps(
                    {
                        "detail": captured_canonical_event
                    }
                ),
            }
        ]
    }

    with patch(
        "lambdas.worker.lambda_function.publish_response",
        side_effect=capture_response_event,
    ), patch(
        "lambdas.worker.lambda_function.update_processing_status",
    ):
        worker_response = worker_handler(
            sqs_event,
            None,
        )

    print("\nWorker result")
    print(json.dumps(worker_response, indent=2))

    print("\n3. End-to-end simulation completed")
    print(
        json.dumps(
            {
                "correlationId": captured_response_event
                .get("correlation", {})
                .get("correlationId"),
                "status": captured_response_event.get("status"),
                "message": captured_response_event.get("message"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
