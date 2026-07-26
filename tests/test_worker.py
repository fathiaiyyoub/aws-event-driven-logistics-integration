import json
import unittest
from unittest.mock import patch

from lambdas.worker.lambda_function import lambda_handler


class WorkerTests(unittest.TestCase):
    @patch("lambdas.worker.lambda_function.update_processing_status")
    @patch("lambdas.worker.lambda_function.publish_response")
    def test_worker_processes_valid_event(self, mock_publish, mock_update):
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
                "receivedAt": "2026-01-01T10:00:00Z",
            },
            "payload": {"shipmentId": "SHIP-1001"},
        }
        sqs_event = {"Records": [{"messageId": "m1", "body": json.dumps({"detail": canonical_event})}]}
        response = lambda_handler(sqs_event, None)

        self.assertEqual(response, {"batchItemFailures": []})
        mock_publish.assert_called_once()
        statuses = [call.args[1] for call in mock_update.call_args_list]
        self.assertIn("PROCESSING", statuses)


if __name__ == "__main__":
    unittest.main()
