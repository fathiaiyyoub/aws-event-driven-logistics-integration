import unittest
from urllib import error
from unittest.mock import MagicMock, patch

from lambdas.response_processor.delivery import (
    DELIVERY_HANDLERS,
    DeliveryError,
    deliver_response,
)


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


def normalized_config(**overrides):
    config = {
        "partnerId": "partner-001",
        "enabled": True,
        "deliveryMethod": "HTTPS_WEBHOOK",
        "endpointUrl": "https://partner.example/callback",
        "messageFormat": "JSON",
        "secretId": None,
        "timeoutSeconds": 10,
    }
    config.update(overrides)
    return config


class DeliveryStrategyTests(unittest.TestCase):
    def test_registry_contains_only_runtime_supported_methods(self):
        self.assertEqual(
            set(DELIVERY_HANDLERS),
            {"HTTPS_WEBHOOK", "PRIVATE_HTTPS"},
        )

    @patch(
        "lambdas.response_processor.delivery.get_secret",
        return_value={},
    )
    @patch("lambdas.response_processor.delivery.request.urlopen")
    def test_unauthenticated_json_webhook_posts_successfully(
        self, mock_urlopen, mock_secret
    ):
        response = MagicMock()
        response.getcode.return_value = 204
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        result = deliver_response(RESPONSE_EVENT, normalized_config())

        self.assertEqual(result, {"statusCode": 204})
        mock_secret.assert_called_once_with(None)
        outbound_request = mock_urlopen.call_args.args[0]
        self.assertEqual(outbound_request.method, "POST")
        self.assertEqual(
            outbound_request.headers["Content-type"],
            "application/json",
        )
        self.assertNotIn("Authorization", outbound_request.headers)
        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 10)

    @patch(
        "lambdas.response_processor.delivery.get_secret",
        return_value={
            "authorizationHeader": "Bearer hidden",
            "apiKey": "hidden-key",
        },
    )
    @patch("lambdas.response_processor.delivery.request.urlopen")
    def test_authenticated_xml_private_https_uses_credentials(
        self, mock_urlopen, mock_secret
    ):
        response = MagicMock()
        response.getcode.return_value = 200
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        deliver_response(RESPONSE_EVENT, normalized_config(
            deliveryMethod="PRIVATE_HTTPS",
            messageFormat="XML",
            secretId="integrations/partner-001",
            timeoutSeconds=5,
        ))

        outbound_request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            outbound_request.headers["Content-type"],
            "application/xml",
        )
        self.assertEqual(
            outbound_request.headers["Authorization"],
            "Bearer hidden",
        )
        self.assertEqual(
            outbound_request.headers["X-api-key"],
            "hidden-key",
        )
        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 5)

    @patch(
        "lambdas.response_processor.delivery.get_secret",
        return_value={},
    )
    @patch(
        "lambdas.response_processor.delivery.request.urlopen",
        side_effect=error.HTTPError(
            "https://partner.example", 500, "failure", {}, None
        ),
    )
    def test_non_2xx_is_delivery_error(self, mock_urlopen, mock_secret):
        with self.assertRaisesRegex(DeliveryError, "HTTP 500"):
            deliver_response(RESPONSE_EVENT, normalized_config())


if __name__ == "__main__":
    unittest.main()
