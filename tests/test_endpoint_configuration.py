import unittest
from unittest.mock import MagicMock, patch

from lambdas.response_processor.config_store import get_partner_config
from lambdas.response_processor.errors import (
    PartnerConfigurationError,
    UnsupportedDeliveryMethodError,
)


def valid_item(**overrides):
    item = {
        "partnerId": "partner-001",
        "enabled": True,
        "deliveryMethod": "HTTPS_WEBHOOK",
        "endpointUrl": "https://partner.example/callback",
    }
    item.update(overrides)
    return item


class PartnerConfigurationTests(unittest.TestCase):
    def _get(self, item):
        table = MagicMock()
        table.get_item.return_value = {"Item": item}
        with patch(
            "lambdas.response_processor.config_store.CONFIG_TABLE_NAME",
            "PartnerConfigurationTest",
        ), patch(
            "lambdas.response_processor.config_store.dynamodb"
        ) as dynamodb:
            dynamodb.Table.return_value = table
            config = get_partner_config("partner-001")
        return config

    def test_valid_https_webhook_is_normalized_with_defaults(self):
        config = self._get(valid_item())
        self.assertEqual(config["deliveryMethod"], "HTTPS_WEBHOOK")
        self.assertEqual(config["messageFormat"], "JSON")
        self.assertEqual(config["timeoutSeconds"], 10)
        self.assertIsNone(config["secretId"])

    def test_valid_private_https_and_xml_are_normalized(self):
        config = self._get(valid_item(
            deliveryMethod="private_https",
            messageFormat="xml",
            timeoutSeconds="5",
            secretId="integrations/partner-001",
        ))
        self.assertEqual(config["deliveryMethod"], "PRIVATE_HTTPS")
        self.assertEqual(config["messageFormat"], "XML")
        self.assertEqual(config["timeoutSeconds"], 5)

    def test_missing_delivery_method_is_controlled_error(self):
        item = valid_item()
        del item["deliveryMethod"]
        with self.assertRaisesRegex(
            PartnerConfigurationError,
            "deliveryMethod must be a non-empty string",
        ):
            self._get(item)

    def test_unsupported_delivery_method_lists_supported_methods(self):
        with self.assertRaisesRegex(
            UnsupportedDeliveryMethodError,
            "Supported methods: HTTPS_WEBHOOK, PRIVATE_HTTPS",
        ):
            self._get(valid_item(deliveryMethod="SQS"))

    def test_missing_endpoint_url_is_controlled_error(self):
        item = valid_item()
        del item["endpointUrl"]
        with self.assertRaisesRegex(
            PartnerConfigurationError,
            "endpointUrl must be a non-empty string",
        ):
            self._get(item)

    def test_non_https_endpoint_is_rejected(self):
        with self.assertRaisesRegex(
            PartnerConfigurationError,
            "valid https:// URL",
        ):
            self._get(valid_item(
                endpointUrl="http://partner.example/callback"
            ))

    def test_invalid_message_format_is_rejected(self):
        with self.assertRaisesRegex(
            PartnerConfigurationError,
            "messageFormat must be JSON or XML",
        ):
            self._get(valid_item(messageFormat="CSV"))

    def test_invalid_timeout_values_are_rejected(self):
        for timeout in (0, 51, "not-a-number", True):
            with self.subTest(timeout=timeout):
                with self.assertRaises(PartnerConfigurationError):
                    self._get(valid_item(timeoutSeconds=timeout))

    def test_missing_configuration_is_controlled_error(self):
        with self.assertRaisesRegex(
            PartnerConfigurationError,
            "No configuration exists",
        ):
            self._get(None)

    def test_enabled_must_be_boolean_and_defaults_disabled(self):
        for enabled in (None, "true"):
            item = valid_item()
            if enabled is None:
                del item["enabled"]
            else:
                item["enabled"] = enabled
            with self.subTest(enabled=enabled):
                with self.assertRaises(PartnerConfigurationError):
                    self._get(item)


if __name__ == "__main__":
    unittest.main()
