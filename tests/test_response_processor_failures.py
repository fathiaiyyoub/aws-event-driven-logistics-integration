import json
import unittest
from unittest.mock import patch

from lambdas.response_processor.errors import (
    DeliveryError,
    PartnerConfigurationError,
)
from lambdas.response_processor.lambda_function import lambda_handler


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

CONFIG = {
    "partnerId": "partner-001",
    "enabled": True,
    "deliveryMethod": "HTTPS_WEBHOOK",
    "endpointUrl": "https://partner.example/callback",
    "messageFormat": "JSON",
    "secretId": None,
    "timeoutSeconds": 10,
}


def event():
    return {
        "Records": [{
            "messageId": "m1",
            "body": json.dumps({"detail": RESPONSE_EVENT}),
        }]
    }


class ResponseProcessorFailureTests(unittest.TestCase):
    @patch("builtins.print")
    @patch("lambdas.response_processor.lambda_function.update_delivery_status")
    @patch("lambdas.response_processor.lambda_function.mark_delivery_attempt")
    @patch(
        "lambdas.response_processor.lambda_function.get_partner_config",
        side_effect=PartnerConfigurationError(
            "deliveryMethod must be a non-empty string."
        ),
    )
    def test_configuration_failure_does_not_increment_network_attempt(
        self, mock_config, mock_attempt, mock_update, mock_print
    ):
        result = lambda_handler(event(), None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        mock_attempt.assert_not_called()
        self.assertEqual(mock_update.call_args.args[1], "CONFIGURATION_FAILED")
        log_entry = json.loads(mock_print.call_args.args[0])
        self.assertEqual(
            log_entry["errorCategory"],
            "PartnerConfigurationError",
        )
        self.assertNotIn("body", log_entry)

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
        side_effect=DeliveryError("sensitive destination detail"),
    )
    def test_retryable_delivery_failure_is_sanitized(
        self, mock_deliver, mock_config, mock_attempt, mock_update
    ):
        result = lambda_handler(event(), None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        self.assertEqual(mock_update.call_args.args[1], "RETRYING")
        self.assertNotIn(
            "sensitive",
            mock_update.call_args.kwargs["message"],
        )

    @patch("lambdas.response_processor.lambda_function.update_delivery_status")
    @patch(
        "lambdas.response_processor.lambda_function.mark_delivery_attempt",
        return_value=3,
    )
    @patch(
        "lambdas.response_processor.lambda_function.get_partner_config",
        return_value=CONFIG,
    )
    @patch(
        "lambdas.response_processor.lambda_function.deliver_response",
        side_effect=DeliveryError("destination down"),
    )
    def test_terminal_delivery_failure_is_marked_failed(
        self, mock_deliver, mock_config, mock_attempt, mock_update
    ):
        result = lambda_handler(event(), None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        self.assertEqual(mock_update.call_args.args[1], "DELIVERY_FAILED")


if __name__ == "__main__":
    unittest.main()
