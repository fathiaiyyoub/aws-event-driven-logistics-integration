import json
import xml.etree.ElementTree as ET
from typing import Any


class MessageParsingError(ValueError):
    """Raised when an inbound message cannot be parsed."""


def parse_message(message: Any, message_format: str | None = None) -> dict:
    """
    Parse an inbound JSON or XML message into a Python dictionary.

    Supports:
    - Python dictionaries
    - JSON strings
    - XML strings
    """

    if isinstance(message, dict):
        return message

    if isinstance(message, bytes):
        message = message.decode("utf-8")

    if not isinstance(message, str) or not message.strip():
        raise MessageParsingError(
            "The inbound message must be a non-empty JSON or XML payload."
        )

    message = message.strip()
    normalized_format = message_format.upper() if message_format else None

    if normalized_format in (None, "JSON"):
        try:
            parsed_json = json.loads(message)

            if not isinstance(parsed_json, dict):
                raise MessageParsingError(
                    "The JSON payload must contain an object at its top level."
                )

            return parsed_json

        except json.JSONDecodeError as error:
            if normalized_format == "JSON":
                raise MessageParsingError("The inbound JSON payload is malformed.") from error

    if normalized_format in (None, "XML"):
        try:
            root = ET.fromstring(message)
            return _xml_element_to_dict(root)

        except ET.ParseError as error:
            if normalized_format == "XML":
                raise MessageParsingError("The inbound XML payload is malformed.") from error

    raise MessageParsingError(
        "The inbound message is neither valid JSON nor valid XML."
    )


def _xml_element_to_dict(element: ET.Element) -> dict:
    """
    Convert an XML document into a dictionary.

    The outer XML root element is not included, allowing XML and JSON
    partner payloads to produce a similar dictionary structure.
    """

    parsed_message = {}

    for child in element:
        if len(child):
            parsed_message[child.tag] = _xml_element_to_dict(child)
        else:
            parsed_message[child.tag] = (
                child.text.strip()
                if child.text and child.text.strip()
                else None
            )

    return parsed_message
