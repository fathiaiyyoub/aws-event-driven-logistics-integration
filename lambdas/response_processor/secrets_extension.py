import json
import os
from urllib import parse, request, error


EXTENSION_HOST = os.getenv("PARAMETERS_SECRETS_EXTENSION_HTTP_PORT", "2773")
EXTENSION_TIMEOUT_SECONDS = int(os.getenv("SECRETS_EXTENSION_TIMEOUT_SECONDS", "3"))


class CredentialRetrievalError(RuntimeError):
    pass


def get_secret(secret_id: str | None) -> dict:
    """Retrieve cached credentials through the AWS Parameters and Secrets Lambda Extension."""

    if not secret_id:
        return {}

    session_token = os.getenv("AWS_SESSION_TOKEN")
    if not session_token:
        raise CredentialRetrievalError("AWS_SESSION_TOKEN is unavailable.")

    url = (
        f"http://localhost:{EXTENSION_HOST}/secretsmanager/get"
        f"?secretId={parse.quote(secret_id, safe='')}"
    )
    req = request.Request(url, headers={"X-Aws-Parameters-Secrets-Token": session_token})

    try:
        with request.urlopen(req, timeout=EXTENSION_TIMEOUT_SECONDS) as response:
            envelope = json.loads(response.read().decode("utf-8"))
    except (error.URLError, json.JSONDecodeError) as exc:
        raise CredentialRetrievalError(f"Unable to retrieve secret {secret_id} through the Lambda extension.") from exc

    secret_string = envelope.get("SecretString")
    if not secret_string:
        raise CredentialRetrievalError(f"Secret {secret_id} does not contain SecretString.")

    try:
        credentials = json.loads(secret_string)
    except json.JSONDecodeError as exc:
        raise CredentialRetrievalError(f"Secret {secret_id} is not valid JSON.") from exc

    if not isinstance(credentials, dict):
        raise CredentialRetrievalError(
            f"Secret {secret_id} must contain a JSON object."
        )

    for field_name in ("authorizationHeader", "apiKey"):
        value = credentials.get(field_name)
        if value is not None and (
            not isinstance(value, str) or not value.strip()
        ):
            raise CredentialRetrievalError(
                f"Secret {secret_id} field {field_name} "
                "must be a non-empty string."
            )

    return credentials
