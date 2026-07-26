import json
import unittest
from unittest.mock import patch

from lambdas.adapter.lambda_function import lambda_handler as adapter_handler
from lambdas.worker.lambda_function import lambda_handler as worker_handler


class EndToEndTests(unittest.TestCase):
    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.worker.lambda_function.update_processing_status")
    def test_end_to_end_processing(self, mock_update, mock_create_state):
        published_event = {}
        response_event = {}

        def capture_event(event):
            published_event.update(event)
            return {"FailedEntryCount": 0, "Entries": [{"EventId": "evt-local"}]}

        def capture_response(event):
            response_event.update(event)

        inbound_event = {"body": json.dumps({
            "eventType": "CreateShipment",
            "partnerId": "DHL",
            "sourceSystem": "partner.dhl",
            "messageFormat": "JSON",
            "shipmentId": "SHIP-1001",
        })}

        with patch("lambdas.adapter.lambda_function.publish_event", side_effect=capture_event):
            adapter_response = adapter_handler(inbound_event, None)

        sqs_event = {"Records": [{"messageId": "m1", "body": json.dumps({"detail": published_event})}]}
        with patch("lambdas.worker.lambda_function.publish_response", side_effect=capture_response):
            worker_response = worker_handler(sqs_event, None)

        self.assertEqual(adapter_response["statusCode"], 202)
        self.assertEqual(worker_response, {"batchItemFailures": []})
        self.assertEqual(response_event["correlation"]["partnerId"], "DHL")
        self.assertIn(response_event["status"], ["SUCCESS", "PROCESSING_FAILED", "VALIDATION_FAILED"])


if __name__ == "__main__":
    unittest.main()
