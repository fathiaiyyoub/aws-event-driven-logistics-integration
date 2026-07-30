import unittest
from unittest.mock import patch

from lambdas.common.state_store import CLAIM_ACQUIRED, CLAIM_EXHAUSTED
from lambdas.response_processor.errors import DeliveryError
from lambdas.response_processor.lambda_function import lambda_handler
from tests.test_response_processor import CONFIG, response_record


class ResponseProcessorFailureTests(unittest.TestCase):
    @patch("lambdas.response_processor.lambda_function.fail_delivery")
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
        side_effect=DeliveryError("sensitive destination detail"),
    )
    def test_webhook_failure_records_retry_and_returns_batch_failure(
        self, mock_deliver, mock_config, mock_claim, mock_fail
    ):
        result = lambda_handler({"Records": [response_record()]}, None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        self.assertEqual(mock_fail.call_args.args[3], "RETRYING")
        self.assertNotIn("sensitive", mock_fail.call_args.args[4])

    @patch("lambdas.response_processor.lambda_function.fail_delivery")
    @patch(
        "lambdas.response_processor.lambda_function.claim_delivery",
        return_value={"status": CLAIM_ACQUIRED, "attempt": 3},
    )
    @patch(
        "lambdas.response_processor.lambda_function.get_partner_config",
        return_value=CONFIG,
    )
    @patch(
        "lambdas.response_processor.lambda_function.deliver_response",
        side_effect=DeliveryError("destination down"),
    )
    def test_final_attempt_is_failed_and_left_for_dlq(
        self, mock_deliver, mock_config, mock_claim, mock_fail
    ):
        result = lambda_handler({"Records": [response_record()]}, None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        self.assertEqual(mock_fail.call_args.args[3], "DELIVERY_FAILED")

    @patch("lambdas.response_processor.lambda_function.deliver_response")
    @patch(
        "lambdas.response_processor.lambda_function.claim_delivery",
        return_value={"status": CLAIM_EXHAUSTED, "attempt": None},
    )
    def test_exhausted_message_fails_without_more_webhooks(
        self, mock_claim, mock_deliver
    ):
        result = lambda_handler({"Records": [response_record()]}, None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        mock_deliver.assert_not_called()

    @patch("lambdas.response_processor.lambda_function.complete_delivery")
    @patch("lambdas.response_processor.lambda_function.fail_delivery")
    @patch(
        "lambdas.response_processor.lambda_function.claim_delivery",
        side_effect=[
            {"status": CLAIM_ACQUIRED, "attempt": 1},
            {"status": CLAIM_ACQUIRED, "attempt": 1},
        ],
    )
    @patch(
        "lambdas.response_processor.lambda_function.get_partner_config",
        return_value=CONFIG,
    )
    @patch(
        "lambdas.response_processor.lambda_function.deliver_response",
        side_effect=[DeliveryError("down"), {"statusCode": 204}],
    )
    def test_partial_batch_failure_does_not_retry_success(
        self, mock_deliver, mock_config, mock_claim, mock_fail, mock_complete
    ):
        result = lambda_handler(
            {"Records": [response_record("bad"), response_record("good")]},
            None,
        )

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "bad"}]},
        )
        mock_complete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
