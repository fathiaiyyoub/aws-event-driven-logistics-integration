import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from lambdas.common import state_store


def conditional_failure():
    return ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "condition failed",
            }
        },
        "UpdateItem",
    )


class StateStoreTests(unittest.TestCase):
    @patch("lambdas.common.state_store._table")
    def test_initial_state_supports_independent_claims(self, mock_table_factory):
        table = MagicMock()
        mock_table_factory.return_value = table
        event = {
            "eventId": "evt-1",
            "eventType": "CreateShipment",
            "correlation": {
                "correlationId": "corr-1",
                "partnerId": "DHL",
            },
        }

        state_store.create_message_state(event)

        kwargs = table.put_item.call_args.kwargs
        self.assertEqual(kwargs["Item"]["processingStatus"], "RECEIVED")
        self.assertEqual(kwargs["Item"]["deliveryStatus"], "PENDING")
        self.assertEqual(kwargs["Item"]["deliveryAttemptCount"], 0)
        self.assertEqual(
            kwargs["ConditionExpression"],
            "attribute_not_exists(correlationId)",
        )

    @patch("lambdas.common.state_store._table")
    def test_processing_claim_is_atomic_and_has_token_and_lease(
        self, mock_table_factory
    ):
        table = MagicMock()
        mock_table_factory.return_value = table

        result = state_store.claim_processing(
            "corr-1", "evt-1", "token-1", 120, now_epoch=1000
        )

        self.assertEqual(result, state_store.CLAIM_ACQUIRED)
        kwargs = table.update_item.call_args.kwargs
        self.assertEqual(kwargs["ExpressionAttributeValues"][":token"], "token-1")
        self.assertEqual(kwargs["ExpressionAttributeValues"][":expires"], 1120)
        self.assertIn("processingClaimExpiresAt <= :now", kwargs["ConditionExpression"])
        self.assertIn("processingStatus <> :completed", kwargs["ConditionExpression"])

    @patch("lambdas.common.state_store._table")
    def test_concurrent_processing_claim_is_busy(self, mock_table_factory):
        table = MagicMock()
        table.update_item.side_effect = conditional_failure()
        table.get_item.return_value = {
            "Item": {
                "requestEventId": "evt-1",
                "processingStatus": "PROCESSING",
                "processingClaimToken": "other-token",
                "processingClaimExpiresAt": 1100,
            }
        }
        mock_table_factory.return_value = table

        result = state_store.claim_processing(
            "corr-1", "evt-1", "token-2", 120, now_epoch=1000
        )

        self.assertEqual(result, state_store.CLAIM_BUSY)
        self.assertTrue(table.get_item.call_args.kwargs["ConsistentRead"])

    @patch("lambdas.common.state_store._table")
    def test_completed_processing_duplicate_is_suppressed(self, mock_table_factory):
        table = MagicMock()
        table.update_item.side_effect = conditional_failure()
        table.get_item.return_value = {
            "Item": {
                "requestEventId": "evt-1",
                "processingStatus": "COMPLETED",
            }
        }
        mock_table_factory.return_value = table

        result = state_store.claim_processing(
            "corr-1", "evt-1", "token-2", 120, now_epoch=1000
        )

        self.assertEqual(result, state_store.CLAIM_COMPLETED)

    @patch("lambdas.common.state_store._table")
    def test_expired_processing_lease_can_be_recovered(self, mock_table_factory):
        table = MagicMock()
        mock_table_factory.return_value = table

        result = state_store.claim_processing(
            "corr-1", "evt-1", "new-token", 120, now_epoch=1100
        )

        self.assertEqual(result, state_store.CLAIM_ACQUIRED)
        values = table.update_item.call_args.kwargs["ExpressionAttributeValues"]
        self.assertEqual(values[":now"], 1100)
        self.assertEqual(values[":expires"], 1220)

    @patch("lambdas.common.state_store._table")
    def test_stale_processing_token_is_rejected(self, mock_table_factory):
        table = MagicMock()
        table.update_item.side_effect = conditional_failure()
        mock_table_factory.return_value = table

        with self.assertRaises(state_store.ClaimOwnershipError):
            state_store.complete_processing(
                "corr-1", "stale-token", "done", "response-1"
            )

        condition = table.update_item.call_args.kwargs["ConditionExpression"]
        self.assertEqual(
            condition,
            "processingStatus = :processing AND processingClaimToken = :token",
        )

        with self.assertRaises(state_store.ClaimOwnershipError):
            state_store.fail_processing("corr-1", "stale-token", "failed")

    @patch("lambdas.common.state_store._table")
    def test_delivery_claim_is_atomic_and_increments_attempt(self, mock_table_factory):
        table = MagicMock()
        table.update_item.return_value = {
            "Attributes": {"deliveryAttemptCount": 2}
        }
        mock_table_factory.return_value = table

        result = state_store.claim_delivery(
            "corr-1", "response-1", "token-1", 120, 3, now_epoch=1000
        )

        self.assertEqual(
            result,
            {"status": state_store.CLAIM_ACQUIRED, "attempt": 2},
        )
        kwargs = table.update_item.call_args.kwargs
        self.assertIn("ADD deliveryAttemptCount :one", kwargs["UpdateExpression"])
        self.assertIn("deliveryAttemptCount < :maxAttempts", kwargs["ConditionExpression"])
        self.assertIn("deliveryClaimExpiresAt <= :now", kwargs["ConditionExpression"])

    @patch("lambdas.common.state_store._table")
    def test_delivered_duplicate_is_suppressed(self, mock_table_factory):
        table = MagicMock()
        table.update_item.side_effect = conditional_failure()
        table.get_item.return_value = {
            "Item": {
                "deliveryId": "response-1",
                "deliveryStatus": "DELIVERED",
                "deliveryAttemptCount": 1,
            }
        }
        mock_table_factory.return_value = table

        result = state_store.claim_delivery(
            "corr-1", "response-1", "token-2", 120, 3, now_epoch=1000
        )

        self.assertEqual(result["status"], state_store.CLAIM_DELIVERED)

    @patch("lambdas.common.state_store._table")
    def test_expired_delivery_lease_can_be_recovered(self, mock_table_factory):
        table = MagicMock()
        table.update_item.return_value = {
            "Attributes": {"deliveryAttemptCount": 2}
        }
        mock_table_factory.return_value = table

        result = state_store.claim_delivery(
            "corr-1", "response-1", "new-token", 120, 3, now_epoch=1100
        )

        self.assertEqual(result["status"], state_store.CLAIM_ACQUIRED)
        values = table.update_item.call_args.kwargs["ExpressionAttributeValues"]
        self.assertEqual(values[":expires"], 1220)

    @patch("lambdas.common.state_store._table")
    def test_stale_delivery_token_is_rejected(self, mock_table_factory):
        table = MagicMock()
        table.update_item.side_effect = conditional_failure()
        mock_table_factory.return_value = table

        with self.assertRaises(state_store.ClaimOwnershipError):
            state_store.complete_delivery(
                "corr-1", "response-1", "stale-token", "done", 200
            )

        condition = table.update_item.call_args.kwargs["ConditionExpression"]
        self.assertIn("deliveryClaimToken = :token", condition)
        self.assertIn("deliveryId = :deliveryId", condition)

        with self.assertRaises(state_store.ClaimOwnershipError):
            state_store.fail_delivery(
                "corr-1",
                "response-1",
                "stale-token",
                "RETRYING",
                "failed",
            )

    @patch("lambdas.common.state_store._table")
    def test_maximum_attempts_are_dlq_compatible(self, mock_table_factory):
        table = MagicMock()
        table.update_item.side_effect = conditional_failure()
        table.get_item.return_value = {
            "Item": {
                "deliveryId": "response-1",
                "deliveryStatus": "DELIVERY_FAILED",
                "deliveryAttemptCount": 3,
            }
        }
        mock_table_factory.return_value = table

        result = state_store.claim_delivery(
            "corr-1", "response-1", "token-4", 120, 3, now_epoch=1000
        )

        self.assertEqual(result["status"], state_store.CLAIM_EXHAUSTED)


if __name__ == "__main__":
    unittest.main()
