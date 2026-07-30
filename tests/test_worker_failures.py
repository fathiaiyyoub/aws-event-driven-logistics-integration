import unittest
from unittest.mock import patch

from lambdas.common.state_store import CLAIM_ACQUIRED
from lambdas.worker.lambda_function import lambda_handler
from tests.test_worker import canonical_event, record


class WorkerFailureTests(unittest.TestCase):
    @patch("lambdas.worker.lambda_function.complete_processing")
    @patch("lambdas.worker.lambda_function.publish_response")
    @patch(
        "lambdas.worker.lambda_function.claim_processing",
        return_value=CLAIM_ACQUIRED,
    )
    def test_validation_failure_is_a_completed_business_response(
        self, mock_claim, mock_publish, mock_complete
    ):
        invalid = canonical_event()
        invalid["eventType"] = "UnsupportedEvent"

        result = lambda_handler(
            {"Records": [record(event=invalid)]},
            None,
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(mock_publish.call_args.args[0]["status"], "VALIDATION_FAILED")
        mock_complete.assert_called_once()

    @patch("lambdas.worker.lambda_function.fail_processing")
    @patch("lambdas.worker.lambda_function.publish_response", side_effect=RuntimeError("down"))
    @patch(
        "lambdas.worker.lambda_function.claim_processing",
        return_value=CLAIM_ACQUIRED,
    )
    def test_publish_failure_releases_owned_claim_for_retry(
        self, mock_claim, mock_publish, mock_fail
    ):
        result = lambda_handler({"Records": [record()]}, None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "m1"}]},
        )
        mock_fail.assert_called_once()

    @patch("lambdas.worker.lambda_function.complete_processing")
    @patch("lambdas.worker.lambda_function.fail_processing")
    @patch(
        "lambdas.worker.lambda_function.publish_response",
        side_effect=[RuntimeError("down"), None],
    )
    @patch(
        "lambdas.worker.lambda_function.claim_processing",
        return_value=CLAIM_ACQUIRED,
    )
    def test_processing_failure_can_retry_successfully(
        self, mock_claim, mock_publish, mock_fail, mock_complete
    ):
        first = lambda_handler({"Records": [record("first")]}, None)
        retry = lambda_handler({"Records": [record("retry")]}, None)

        self.assertEqual(
            first,
            {"batchItemFailures": [{"itemIdentifier": "first"}]},
        )
        self.assertEqual(retry, {"batchItemFailures": []})
        mock_fail.assert_called_once()
        mock_complete.assert_called_once()

    @patch("lambdas.worker.lambda_function.complete_processing")
    @patch("lambdas.worker.lambda_function.publish_response")
    @patch(
        "lambdas.worker.lambda_function.claim_processing",
        return_value=CLAIM_ACQUIRED,
    )
    def test_partial_batch_failure_does_not_retry_success(
        self, mock_claim, mock_publish, mock_complete
    ):
        bad = {"messageId": "bad", "body": "not-json"}
        result = lambda_handler({"Records": [bad, record("good")]}, None)

        self.assertEqual(
            result,
            {"batchItemFailures": [{"itemIdentifier": "bad"}]},
        )
        mock_publish.assert_called_once()
        mock_complete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
