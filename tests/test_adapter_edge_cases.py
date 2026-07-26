import json
import unittest
from unittest.mock import patch

from lambdas.adapter.lambda_function import lambda_handler


class AdapterEdgeCaseTests(unittest.TestCase):
    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_preserves_supplied_correlation_id(self, mock_publish, mock_state):
        event = {"body": json.dumps({
            "eventType": "CreateShipment",
            "partnerId": "DHL",
            "sourceSystem": "partner.dhl",
            "messageFormat": "JSON",
            "correlationId": "corr-existing",
            "shipmentId": "SHIP-1",
        })}

        response = lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 202)
        published = mock_publish.call_args.args[0]
        self.assertEqual(
            published["correlation"]["correlationId"],
            "corr-existing",
        )
        self.assertEqual(published["correlation"]["partnerId"], "DHL")

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_explicit_partner_id_takes_priority(
        self, mock_publish, mock_state
    ):
        event = {"body": json.dumps({
            "eventType": "CreateShipment",
            "partnerId": "DHL",
            "sourceSystem": "legacy.oms",
            "messageFormat": "XML",
            "shipmentId": "SHIP-2",
        })}

        response = lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 202)
        published = mock_publish.call_args.args[0]
        self.assertEqual(
            published["correlation"]["partnerId"],
            "DHL",
        )
        self.assertEqual(published["correlation"]["originalFormat"], "XML")

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_malformed_json_returns_400_before_side_effects(
        self, mock_publish, mock_state
    ):
        response = lambda_handler({
            "httpMethod": "POST",
            "path": "/shipments",
            "headers": {"content-type": "application/json"},
            "body": "{not-json",
        }, None)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["errorCode"],
            "INVALID_REQUEST",
        )
        mock_state.assert_not_called()
        mock_publish.assert_not_called()

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_unsupported_content_type_returns_415(
        self, mock_publish, mock_state
    ):
        response = lambda_handler({
            "httpMethod": "POST",
            "path": "/shipments",
            "headers": {"Content-Type": "text/plain"},
            "body": "not an intentionally supported partner format",
        }, None)

        self.assertEqual(response["statusCode"], 415)
        self.assertEqual(
            json.loads(response["body"])["errorCode"],
            "UNSUPPORTED_MEDIA_TYPE",
        )
        mock_state.assert_not_called()
        mock_publish.assert_not_called()

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_event_source_is_partner_identity_fallback(
        self, mock_publish, mock_state
    ):
        response = lambda_handler({
            "httpMethod": "POST",
            "path": "/shipments",
            "headers": {"content-type": "application/json"},
            "body": json.dumps({
                "eventType": "CreateShipment",
                "eventSource": "partner-fallback",
                "payload": {"shipmentId": "SHP-4"},
            }),
        }, None)

        self.assertEqual(response["statusCode"], 202)
        correlation = mock_publish.call_args.args[0]["correlation"]
        self.assertEqual(correlation["partnerId"], "partner-fallback")
        mock_state.assert_called_once()

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_missing_partner_identity_returns_400(
        self, mock_publish, mock_state
    ):
        response = lambda_handler({"body": json.dumps({
            "eventType": "CreateShipment",
            "shipmentId": "SHIP-3",
        })}, None)

        self.assertEqual(response["statusCode"], 400)
        mock_state.assert_not_called()
        mock_publish.assert_not_called()

    @patch(
        "lambdas.adapter.lambda_function.create_message_state",
        side_effect=RuntimeError("DynamoDB unavailable"),
    )
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_internal_failure_returns_sanitised_500(
        self, mock_publish, mock_state
    ):
        response = lambda_handler({"body": json.dumps({
            "eventType": "CreateShipment",
            "eventSource": "partner-internal",
            "payload": {"shipmentId": "SHIP-5"},
        })}, None)

        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(
            json.loads(response["body"])["errorCode"],
            "INTERNAL_ERROR",
        )
        self.assertNotIn("DynamoDB", response["body"])
        mock_publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
