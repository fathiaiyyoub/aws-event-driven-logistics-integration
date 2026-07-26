import base64
import binascii
import json
import logging

from .parser import parse_message
from .formatter import format_canonical_event
from .correlation import get_correlation_metadata
from .publisher import publish_event
from lambdas.common.state_store import create_message_state


logger = logging.getLogger(__name__)


class UnsupportedContentType(ValueError):
    """Raised when a partner sends a media type the Adapter does not support."""


def _header(event, name):
    for header_name, value in (event.get("headers") or {}).items():
        if header_name.lower() == name.lower():
            return value
    for header_name, values in (event.get("multiValueHeaders") or {}).items():
        if header_name.lower() == name.lower() and values:
            return values[-1]
    return None


def _content_type(event):
    value = _header(event, "Content-Type")
    return value.split(";", 1)[0].strip().lower() if value else None


def _message_format(event):
    content_type = _content_type(event)
    if content_type is None:
        return None
    if content_type == "application/json" or content_type.endswith("+json"):
        return "JSON"
    if content_type in {"application/xml", "text/xml"} or content_type.endswith("+xml"):
        return "XML"
    raise UnsupportedContentType("The request Content-Type is not supported.")


def _request_metadata(event):
    """Return safe diagnostic fields without copying headers or body content."""

    if not isinstance(event, dict):
        return {"eventEnvelopeType": type(event).__name__}

    request_context = event.get("requestContext")
    request_context = request_context if isinstance(request_context, dict) else {}
    http_context = request_context.get("http")
    http_context = http_context if isinstance(http_context, dict) else {}

    if event.get("version") == "2.0":
        envelope_type = "APIGatewayV2"
    elif "httpMethod" in event:
        envelope_type = "APIGatewayV1"
    elif "body" in event:
        envelope_type = "MappedBody"
    else:
        envelope_type = "Direct"

    return {
        "eventEnvelopeType": envelope_type,
        "httpMethod": event.get("httpMethod") or http_context.get("method"),
        "path": event.get("path") or event.get("rawPath"),
        "requestId": request_context.get("requestId"),
        "isBase64Encoded": event.get("isBase64Encoded") is True,
        "contentType": _content_type(event),
    }


def _extract_message(event):
    """Extract a partner message from API Gateway or direct invocation input."""

    if not isinstance(event, dict):
        raise ValueError("The Lambda event must be a JSON object.")

    message = event["body"] if "body" in event else event

    if event.get("isBase64Encoded") is True:
        if not isinstance(message, str):
            raise ValueError("A base64-encoded request body must be a string.")
        try:
            message = base64.b64decode(message, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as error:
            raise ValueError("The request body is not valid base64-encoded UTF-8.") from error

    return message


def _normalise_request(event):
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}
    method = (event.get("httpMethod") or http_context.get("method") or "").upper()
    path_parameters = event.get("pathParameters") or {}

    if method == "GET":
        return {
            "eventType": "RetrieveShipment",
            "eventSource": _header(event, "X-Partner-Id"),
            "messageFormat": "JSON",
            "payload": {"shipmentId": path_parameters.get("shipmentId")},
        }

    message_format = _message_format(event)
    message = parse_message(_extract_message(event), message_format)
    message["messageFormat"] = message_format or message.get("messageFormat", "JSON")
    if not any(message.get(field) for field in ("partnerId", "sourceSystem", "eventSource")):
        message["eventSource"] = _header(event, "X-Partner-Id")

    shipment_id = path_parameters.get("shipmentId")
    if shipment_id:
        payload = message.setdefault("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("The payload field must be an object.")
        payload.setdefault("shipmentId", shipment_id)

    return message


def _validate_request(message, method):
    event_type = message.get("eventType")
    payload = message.get("payload")
    if payload is None:
        metadata_fields = {
            "eventId", "correlationId", "eventType", "eventSource",
            "partnerId", "sourceSystem", "messageFormat",
            "timestamp",
        }
        payload = {
            key: value
            for key, value in message.items()
            if key not in metadata_fields
        }

    if not event_type or not isinstance(payload, dict):
        raise ValueError("eventType and an object payload are required.")

    expected_type = {
        "POST": "CreateShipment",
        "PUT": "UpdateShipmentStatus",
        "GET": "RetrieveShipment",
    }.get(method)
    if expected_type and event_type != expected_type:
        raise ValueError("The event type does not match the API operation.")

    required_payload_fields = {
        "CreateShipment": ("shipmentId",),
        "UpdateShipmentStatus": ("shipmentId", "status"),
        "RetrieveShipment": ("shipmentId",),
    }.get(event_type, ())
    if any(not payload.get(field) for field in required_payload_fields):
        raise ValueError("The request payload is missing required fields.")


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    """Inbound path of the bidirectional Adapter Lambda."""

    stage = "extract"
    metadata = _request_metadata(event)
    correlation = None
    correlation_id = _header(event, "X-Correlation-Id") if isinstance(event, dict) else None

    try:
        parsed_message = _normalise_request(event)
        correlation_id = parsed_message.get("correlationId") or correlation_id
        stage = "validate"
        _validate_request(parsed_message, (metadata.get("httpMethod") or "").upper())
        stage = "correlate"
        correlation = get_correlation_metadata(parsed_message)
        stage = "format"
        canonical_event = format_canonical_event(parsed_message, correlation)

        # Persist the durable lifecycle before publishing downstream.
        stage = "create_state"
        create_message_state(canonical_event)
        stage = "publish"
        publish_event(canonical_event)
    except UnsupportedContentType as error:
        logger.warning(
            "Adapter rejected unsupported content type at stage=%s "
            "correlationId=%s errorType=%s metadata=%s",
            stage,
            correlation["correlationId"] if correlation else correlation_id,
            type(error).__name__,
            metadata,
        )
        return _response(415, {
            "message": "Unsupported content type.",
            "errorCode": "UNSUPPORTED_MEDIA_TYPE",
        })
    except ValueError as error:
        logger.warning(
            "Adapter rejected invalid request at stage=%s correlationId=%s "
            "errorType=%s metadata=%s",
            stage,
            correlation["correlationId"] if correlation else correlation_id,
            type(error).__name__,
            metadata,
        )
        return _response(400, {
            "message": "Invalid request.",
            "errorCode": "INVALID_REQUEST",
        })
    except Exception as error:
        logger.error(
            "Adapter request processing failed at stage=%s correlationId=%s "
            "errorType=%s metadata=%s",
            stage,
            correlation["correlationId"] if correlation else correlation_id,
            type(error).__name__,
            metadata,
        )
        return _response(500, {
            "message": "The request could not be processed.",
            "errorCode": "INTERNAL_ERROR",
        })

    return _response(202, {
        "message": "Request accepted for asynchronous processing.",
        "correlationId": correlation["correlationId"],
        "eventId": canonical_event["eventId"],
    })
