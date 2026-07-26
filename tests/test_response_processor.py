import json
import unittest
from unittest.mock import patch

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


def sqs_event():
    return {
        "Records": [{
            "messageId": "m1",
            "body": json.dumps({"detail": RESPONSE_EVENT}),
        }]
    }


class ResponseProcessorTests(unittest.TestCase):
    @patch("lambdas.response_processor.lambda_function.update_delivery_status")
    @patch(
        "lambdas.response_processor.lambda_function.mark_delivery_attempt",
        return_value=1,
    )
    @patch(
        "lambdas.response_processor.lambda_function.get_partner_config",
        return_value=CONFIG,
    )
    @patch(
        "lambdas.response_processor.lambda_function.deliver_response",
        return_value={"statusCode": 204},
    )
    def test_successful_delivery_updates_state(
        self, mock_deliver, mock_config, mock_attempt, mock_update
    ):
        result = lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        mock_config.assert_called_once_with("partner-001")
        mock_attempt.assert_called_once_with("corr-1")
        mock_deliver.assert_called_once_with(RESPONSE_EVENT, CONFIG)
        self.assertEqual(mock_update.call_args.args[1], "DELIVERED")
        self.assertEqual(
            mock_update.call_args.kwargs["destination_status_code"],
            204,
        )


if __name__ == "__main__":
    unittest.main()
