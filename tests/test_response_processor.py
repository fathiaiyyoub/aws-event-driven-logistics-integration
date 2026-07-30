import json
import unittest
from unittest.mock import patch

from lambdas.common.state_store import (
    CLAIM_ACQUIRED,
    CLAIM_BUSY,
    CLAIM_DELIVERED,
)
from lambdas.response_processor.lambda_function import lambda_handler


CONFIG = {
    "partnerId": "partner-001",
    "enabled": True,
    "deliveryMethod": "HTTPS_WEBHOOK",
    "endpointUrl": "https://partner.example/callback",
    "messageFormat": "JSON",
    "secretId": None,
    "timeoutSeconds": 10,
}

RESPONSE_EVENT = {
    "eventId": "response-1",
    "eventType": "ProcessingResponse",
    "eventSource": "legacy.logistics.worker",
    "timestamp": "2026-01-01T10:05:00Z",
    "correlation": {
        "correlationId": "corr-1",
        "partnerId": "partner-001",
        "sourceSystem": "partner-001",
        "originalFormat": "JSON",
        "receivedAt": "2026-01-01T10:00:00Z",
    },
    "requestEventId": "request-1",
    "requestEventType": "CreateShipment",
    "status": "SUCCESS",
    "message": "Shipment processed successfully.",
    "payload": {"shipmentId": "SHIP-1"},
}


def response_record(message_id="m1"):
    return {
        "messageId": message_id,
        "body": json.dumps({"detail": RESPONSE_EVENT}),
    }


class ResponseProcessorTests(unittest.TestCase):
    @patch("lambdas.response_processor.lambda_function.complete_delivery")
    @patch(
        "lambdas.response_processor.lambda_function.claim_delivery",
        return_value={"status": CLAIM_ACQUIRED, "attempt": 1},
    )
    @patch(
        "lambdas.response_processor.lambda_function.get_partner_config",
        return_value=CONFIG,
    )
    @patch(
        "lambdas.response_processor.lambda_function.deliver_response",
        return_value={"statusCode": 204},
    )
    def test_success_uses_delivery_id_as_idempotency_key(
        self, mock_deliver, mock_config, mock_claim, mock_complete
    ):
        result = lambda_handler({"Records": [response_record()]}, None)

        self.assertEqual(result, {"batchItemFailures": []})
        mock_deliver.assert_called_once_with(
            RESPONSE_EVENT,
            CONFIG,
            "response-1",
        )
        self.assertEqual(mock_complete.call_args.args[1], "response-1")

    @patch("lambdas.response_processor.lambda_function.deliver_response")
    @patch(
        "lambdas.response_processor.lambda_function.claim_delivery",
        side_effect=[
            {"status": CLAIM_ACQUIRED, "attempt": 1},
            {"status": CLAIM_DELIVERED, "attempt": None},
        ],
    )
    @patch(
        "lambdas.response_processor.lambda_function.get_partner_config",
        return_value=CONFIG,
    )
    @patch("lambdas.response_processor.lambda_function.complete_delivery")
    def test_duplicate_after_delivered_is_suppressed(
        self, mock_complete, mock_config, mock_claim, mock_deliver
    ):
        mock_deliver.return_value = {"statusCode": 204}
        result = lambda_handler(
            {"Records": [response_record("m1"), response_record("m2")]},
            None,
        )

        self.assertEqual(result, {"batchItemFailures": []})
        mock_deliver.assert_called_once()
        mock_complete.assert_called_once()

    @patch("lambdas.response_processor.lambda_function.deliver_response")
    @patch(
        "lambdas.response_processor.lambda_function.claim_delivery",
        return_value={"status": CLAIM_BUSY, "attempt": None},
    )
    def test_concurrent_delivery_claim_is_retryable(self, mock_claim, mock_deliver):
        result = lambda_handler({"Records": [response_record()]}, None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        mock_deliver.assert_not_called()


if __name__ == "__main__":
    unittest.main()
