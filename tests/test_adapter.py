import base64
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from lambdas.adapter.lambda_function import lambda_handler


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "payloads"
    / "api_gateway_test_event.json"
)


class AdapterTests(unittest.TestCase):
    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_rest_v1_proxy_post_fixture_is_persisted_and_published(
        self, mock_publish, mock_create_state
    ):
        event = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        response = lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 202)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        self.assertIsInstance(json.loads(response["body"]), dict)
        mock_create_state.assert_called_once()
        mock_publish.assert_called_once()
        canonical_event = mock_publish.call_args.args[0]
        self.assertEqual(canonical_event["eventType"], "CreateShipment")
        self.assertEqual(canonical_event["eventSource"], "partner-001")
        self.assertEqual(canonical_event["correlation"]["partnerId"], "partner-001")
        self.assertEqual(canonical_event["payload"]["shipmentId"], "SHP-10001")

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_rest_v1_proxy_put_uses_path_shipment_id(
        self, mock_publish, mock_create_state
    ):
        event = {
            "httpMethod": "PUT",
            "path": "/shipments/SHP-2/status",
            "pathParameters": {"shipmentId": "SHP-2"},
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps({
                "eventType": "UpdateShipmentStatus",
                "eventSource": "partner-002",
                "payload": {"status": "IN_TRANSIT"},
            }),
            "isBase64Encoded": False,
        }

        response = lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 202)
        canonical_event = mock_publish.call_args.args[0]
        self.assertEqual(canonical_event["payload"]["shipmentId"], "SHP-2")
        self.assertEqual(canonical_event["payload"]["status"], "IN_TRANSIT")
        mock_create_state.assert_called_once()

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_rest_v1_proxy_get_uses_header_and_path_metadata(
        self, mock_publish, mock_create_state
    ):
        event = {
            "httpMethod": "GET",
            "path": "/shipments/SHP-3",
            "pathParameters": {"shipmentId": "SHP-3"},
            "headers": {"x-partner-id": "partner-003"},
            "body": None,
            "isBase64Encoded": False,
        }

        response = lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 202)
        canonical_event = mock_publish.call_args.args[0]
        self.assertEqual(canonical_event["eventType"], "RetrieveShipment")
        self.assertEqual(canonical_event["eventSource"], "partner-003")
        self.assertEqual(canonical_event["payload"], {"shipmentId": "SHP-3"})
        mock_create_state.assert_called_once()

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_xml_request_is_parsed(self, mock_publish, mock_create_state):
        event = {
            "httpMethod": "POST",
            "path": "/shipments",
            "headers": {"CONTENT-TYPE": "application/xml"},
            "body": (
                "<Shipment><eventType>CreateShipment</eventType>"
                "<eventSource>PartnerA</eventSource>"
                "<shipmentId>SHIP-2001</shipmentId></Shipment>"
            ),
            "isBase64Encoded": False,
        }

        response = lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 202)
        canonical_event = mock_publish.call_args.args[0]
        self.assertEqual(canonical_event["payload"]["shipmentId"], "SHIP-2001")
        self.assertEqual(canonical_event["correlation"]["originalFormat"], "XML")
        mock_create_state.assert_called_once()

    @patch("lambdas.adapter.lambda_function.create_message_state")
    @patch("lambdas.adapter.lambda_function.publish_event")
    def test_base64_encoded_json_body_is_decoded(
        self, mock_publish, mock_create_state
    ):
        body = json.dumps({
            "eventType": "CreateShipment",
            "eventSource": "partner-base64",
            "payload": {"shipmentId": "SHP-64"},
        }).encode("utf-8")
        event = {
            "httpMethod": "POST",
            "path": "/shipments",
            "headers": {"content-type": "application/json"},
            "body": base64.b64encode(body).decode("ascii"),
            "isBase64Encoded": True,
        }

        response = lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 202)
        self.assertEqual(
            mock_publish.call_args.args[0]["payload"]["shipmentId"],
            "SHP-64",
        )
        mock_create_state.assert_called_once()


if __name__ == "__main__":
    unittest.main()
