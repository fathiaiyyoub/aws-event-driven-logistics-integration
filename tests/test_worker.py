import json
import unittest
from unittest.mock import patch

from lambdas.common.state_store import (
    CLAIM_ACQUIRED,
    CLAIM_BUSY,
    CLAIM_COMPLETED,
)
from lambdas.worker.lambda_function import lambda_handler
from lambdas.worker.response import build_response_event


def canonical_event(event_id="evt-1001", correlation_id="corr-1001"):
    return {
        "eventId": event_id,
        "eventType": "CreateShipment",
        "eventSource": "partner.dhl",
        "timestamp": "2026-01-01T10:00:00Z",
        "correlation": {
            "correlationId": correlation_id,
            "partnerId": "DHL",
            "sourceSystem": "partner.dhl",
            "originalFormat": "JSON",
            "receivedAt": "2026-01-01T10:00:00Z",
        },
        "payload": {"shipmentId": "SHIP-1001"},
    }


def record(message_id="m1", event=None):
    return {
        "messageId": message_id,
        "body": json.dumps({"detail": event or canonical_event()}),
    }


class WorkerTests(unittest.TestCase):
    @patch("lambdas.worker.lambda_function.complete_processing")
    @patch("lambdas.worker.lambda_function.publish_response")
    @patch(
        "lambdas.worker.lambda_function.claim_processing",
        return_value=CLAIM_ACQUIRED,
    )
    def test_worker_processes_and_completes_owned_claim(
        self, mock_claim, mock_publish, mock_complete
    ):
        response = lambda_handler({"Records": [record()]}, None)

        self.assertEqual(response, {"batchItemFailures": []})
        mock_publish.assert_called_once()
        mock_complete.assert_called_once()
        self.assertEqual(
            mock_complete.call_args.args[3],
            mock_publish.call_args.args[0]["eventId"],
        )

    @patch("lambdas.worker.lambda_function.complete_processing")
    @patch("lambdas.worker.lambda_function.publish_response")
    @patch(
        "lambdas.worker.lambda_function.claim_processing",
        side_effect=[CLAIM_ACQUIRED, CLAIM_COMPLETED],
    )
    def test_sequential_duplicate_is_published_once(
        self, mock_claim, mock_publish, mock_complete
    ):
        result = lambda_handler({"Records": [record("m1"), record("m2")]}, None)

        self.assertEqual(result, {"batchItemFailures": []})
        mock_publish.assert_called_once()
        mock_complete.assert_called_once()

    @patch("lambdas.worker.lambda_function.publish_response")
    @patch(
        "lambdas.worker.lambda_function.claim_processing",
        return_value=CLAIM_BUSY,
    )
    def test_concurrent_duplicate_remains_retryable(self, mock_claim, mock_publish):
        result = lambda_handler({"Records": [record()]}, None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        mock_publish.assert_not_called()

    def test_response_id_is_deterministic_and_request_specific(self):
        result = {"status": "SUCCESS", "message": "ok"}
        first = build_response_event(canonical_event("evt-1"), result)
        retry = build_response_event(canonical_event("evt-1"), result)
        other = build_response_event(canonical_event("evt-2"), result)

        self.assertEqual(first["eventId"], retry["eventId"])
        self.assertNotEqual(first["eventId"], other["eventId"])


if __name__ == "__main__":
    unittest.main()
