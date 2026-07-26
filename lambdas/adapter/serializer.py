import json
import xml.etree.ElementTree as ET
from typing import Any


def serialize_response(response: dict, message_format: str) -> str:
    """
    Convert an internal JSON response into the external system's
    required message format.
    """

    normalized_format = message_format.upper()

    if normalized_format == "XML":
        return to_xml(response)

    if normalized_format == "JSON":
        return json.dumps(response)

    raise ValueError(
        f"Unsupported outbound message format: {message_format}"
    )


def to_xml(response: dict) -> str:
    """
    Convert a response dictionary into XML.

    Nested dictionaries are supported for the representative
    portfolio response events.
    """

    root = ET.Element("Response")
    _append_dictionary(root, response)

    return ET.tostring(
        root,
        encoding="unicode",
        xml_declaration=False
    )


def _append_dictionary(parent: ET.Element, data: dict) -> None:
    for key, value in data.items():
        child = ET.SubElement(parent, str(key))

        if isinstance(value, dict):
            _append_dictionary(child, value)

        elif isinstance(value, list):
            for item in value:
                item_element = ET.SubElement(child, "item")

                if isinstance(item, dict):
                    _append_dictionary(item_element, item)
                else:
                    item_element.text = _stringify(item)

        else:
            child.text = _stringify(value)


def _stringify(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return str(value).lower()

    return str(value)