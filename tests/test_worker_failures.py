import json
import unittest
from unittest.mock import patch

from lambdas.worker.lambda_function import lambda_handler


def canonical_event(**overrides):
    event = {
        "eventId": "evt-1",
        "eventType": "CreateShipment",
        "eventSource": "partner.dhl",
        "timestamp": "2026-01-01T00:00:00Z",
        "correlation": {
            "correlationId": "corr-1",
            "partnerId": "DHL",
            "sourceSystem": "partner.dhl",
            "originalFormat": "JSON",
            "receivedAt": "2026-01-01T10:00:00Z",
        },
        "payload": {"shipmentId": "SHIP-1"},
    }
    event.update(overrides)
    return event


class WorkerFailureTests(unittest.TestCase):
    @patch("lambdas.worker.lambda_function.publish_response")
    @patch("lambdas.worker.lambda_function.update_processing_status")
    def test_validation_failure_is_recorded_and_response_is_published(self, mock_update, mock_publish):
        event = canonical_event(eventType="UnsupportedEvent")
        sqs_event = {"Records": [{"messageId": "m1", "body": json.dumps({"detail": event})}]}

        result = lambda_handler(sqs_event, None)

        self.assertEqual(result, {"batchItemFailures": []})
        statuses = [call.args[1] for call in mock_update.call_args_list]
        self.assertEqual(statuses, ["PROCESSING", "VALIDATION_FAILED"])
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args.args[0]["status"], "VALIDATION_FAILED")

    @patch("lambdas.worker.lambda_function.publish_response", side_effect=RuntimeError("EventBridge unavailable"))
    @patch("lambdas.worker.lambda_function.update_processing_status")
    def test_publish_failure_returns_partial_batch_failure(self, mock_update, mock_publish):
        sqs_event = {"Records": [{"messageId": "m1", "body": json.dumps({"detail": canonical_event()})}]}

        with patch("lambdas.worker.lambda_function.process_event", return_value={
            "status": "SUCCESS", "message": "ok", "shipmentId": "SHIP-1"
        }):
            result = lambda_handler(sqs_event, None)

        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": "m1"}]})
        statuses = [call.args[1] for call in mock_update.call_args_list]
        self.assertIn("PROCESSING_FAILED", statuses)

    @patch("lambdas.worker.lambda_function.update_processing_status")
    def test_bad_json_fails_only_the_bad_record(self, mock_update):
        good = {"messageId": "good", "body": json.dumps({"detail": canonical_event()})}
        bad = {"messageId": "bad", "body": "not-json"}

        with patch("lambdas.worker.lambda_function.publish_response"), patch(
            "lambdas.worker.lambda_function.process_event",
            return_value={"status": "SUCCESS", "message": "ok", "shipmentId": "SHIP-1"},
        ):
            result = lambda_handler({"Records": [bad, good]}, None)

        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": "bad"}]})


if __name__ == "__main__":
    unittest.main()
