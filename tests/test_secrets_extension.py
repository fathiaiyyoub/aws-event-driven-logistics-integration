import json
import os
import unittest
from unittest.mock import MagicMock, patch

from lambdas.response_processor.secrets_extension import CredentialRetrievalError, get_secret


class SecretsExtensionTests(unittest.TestCase):
    def test_no_secret_reference_returns_empty_credentials(self):
        self.assertEqual(get_secret(None), {})

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_session_token_is_controlled_error(self):
        with self.assertRaisesRegex(CredentialRetrievalError, "AWS_SESSION_TOKEN"):
            get_secret("integrations/dhl")

    @patch.dict(os.environ, {"AWS_SESSION_TOKEN": "token"}, clear=False)
    @patch("lambdas.response_processor.secrets_extension.request.urlopen")
    def test_valid_secret_is_parsed(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "SecretString": json.dumps({"apiKey": "abc"})
        }).encode("utf-8")
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        secret = get_secret("integrations/dhl")

        self.assertEqual(secret, {"apiKey": "abc"})
        req = mock_urlopen.call_args.args[0]
        self.assertEqual(req.headers["X-aws-parameters-secrets-token"], "token")
        self.assertIn("secretId=integrations%2Fdhl", req.full_url)

    @patch.dict(os.environ, {"AWS_SESSION_TOKEN": "token"}, clear=False)
    @patch("lambdas.response_processor.secrets_extension.request.urlopen")
    def test_malformed_secret_json_is_controlled_error(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({"SecretString": "not-json"}).encode("utf-8")
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        with self.assertRaisesRegex(CredentialRetrievalError, "not valid JSON"):
            get_secret("integrations/dhl")

    @patch.dict(os.environ, {"AWS_SESSION_TOKEN": "token"}, clear=False)
    @patch("lambdas.response_processor.secrets_extension.request.urlopen")
    def test_non_object_secret_json_is_controlled_error(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "SecretString": json.dumps(["not", "an", "object"])
        }).encode("utf-8")
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        with self.assertRaisesRegex(
            CredentialRetrievalError,
            "must contain a JSON object",
        ):
            get_secret("integrations/dhl")


if __name__ == "__main__":
    unittest.main()
