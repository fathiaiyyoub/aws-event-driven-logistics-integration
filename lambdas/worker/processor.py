import random


def process_event(event: dict) -> dict:
    """
    Simulate representative shipment processing.

    This portfolio project intentionally implements only a
    small number of business outcomes to validate the
    integration platform.

    Outcomes:
        - SUCCESS
        - VALIDATION_FAILED
        - PROCESSING_FAILED
    """

    payload = event["payload"]

    shipment_id = payload.get("shipmentId")

    if not shipment_id:
        return {
            "status": "VALIDATION_FAILED",
            "message": "Shipment ID is missing."
        }

    outcome = random.choices(
        population=[
            "SUCCESS",
            "PROCESSING_FAILED"
        ],
        weights=[
            90,
            10
        ],
        k=1
    )[0]

    if outcome == "PROCESSING_FAILED":
        return {
            "status": "PROCESSING_FAILED",
            "message": "A representative processing failure occurred."
        }

    return {
        "status": "SUCCESS",
        "message": "Shipment processed successfully.",
        "shipmentId": shipment_id
    }