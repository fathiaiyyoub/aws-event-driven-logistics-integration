import unittest
from unittest.mock import MagicMock, patch

from lambdas.common import state_store


class StateStoreTests(unittest.TestCase):
    @patch("lambdas.common.state_store._table")
    def test_initial_state_has_separate_processing_and_delivery_statuses(self, mock_table_factory):
        table = MagicMock()
        mock_table_factory.return_value = table
        event = {
            "eventId": "evt-1",
            "eventType": "CreateShipment",
            "eventSource": "partner.dhl",
            "timestamp": "2026-01-01T10:00:00Z",
            "correlation": {
                "correlationId": "corr-1",
                "partnerId": "DHL",
                "sourceSystem": "partner.dhl",
                "originalFormat": "JSON",
                "receivedAt": "2026-01-01T10:00:00Z",
            },
            "payload": {"shipmentId": "SHIP-1"},
        }

        state_store.create_message_state(event)

        kwargs = table.put_item.call_args.kwargs
        item = kwargs["Item"]
        self.assertEqual(item["processingStatus"], "RECEIVED")
        self.assertEqual(item["deliveryStatus"], "PENDING")
        self.assertEqual(item["deliveryAttemptCount"], 0)
        self.assertGreater(item["expiresAt"], 0)
        self.assertEqual(kwargs["ConditionExpression"], "attribute_not_exists(correlationId)")

    @patch("lambdas.common.state_store._table")
    def test_processing_update_does_not_touch_delivery_fields(self, mock_table_factory):
        table = MagicMock()
        mock_table_factory.return_value = table

        state_store.update_processing_status("corr-1", "SUCCESS", "processed")

        expression = table.update_item.call_args.kwargs["UpdateExpression"]
        self.assertIn("processingStatus", expression)
        self.assertNotIn("deliveryStatus", expression)
        self.assertNotIn("deliveryAttemptCount", expression)

    @patch("lambdas.common.state_store._table")
    def test_delivery_update_does_not_touch_processing_fields(self, mock_table_factory):
        table = MagicMock()
        mock_table_factory.return_value = table

        state_store.update_delivery_status("corr-1", "DELIVERED", message="ok", destination_status_code=200)

        expression = table.update_item.call_args.kwargs["UpdateExpression"]
        self.assertIn("deliveryStatus", expression)
        self.assertNotIn("processingStatus", expression)

    @patch("lambdas.common.state_store._table")
    def test_delivery_attempt_counter_is_incremented(self, mock_table_factory):
        table = MagicMock()
        table.update_item.return_value = {"Attributes": {"deliveryAttemptCount": 2}}
        mock_table_factory.return_value = table

        attempt = state_store.mark_delivery_attempt("corr-1")

        self.assertEqual(attempt, 2)
        expression = table.update_item.call_args.kwargs["UpdateExpression"]
        self.assertIn("ADD deliveryAttemptCount", expression)


if __name__ == "__main__":
    unittest.main()
