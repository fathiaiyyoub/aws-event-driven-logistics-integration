from __future__ import annotations

import concurrent.futures
import csv
import json
import os
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REQUEST_COUNT = 150
CONCURRENCY = 10
PARTNER_ID = "partner-001"
TIMEOUT_SECONDS = 30

API_BASE_URL = os.environ.get("LOGISTICS_API_URL", "").rstrip("/")
API_KEY = os.environ.get("LOGISTICS_API_KEY", "")
ENDPOINT = f"{API_BASE_URL}/shipments"

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
OUTPUT_DIR = Path(f"load-test-results-{RUN_ID}")


def send_request(sequence: int) -> dict:
    suffix = f"{RUN_ID}-{sequence:04d}"

    payload = {
        "eventId": f"evt-load-{suffix}",
        "correlationId": f"corr-load-{suffix}",
        "eventType": "CreateShipment",
        "eventSource": "PartnerA",
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "payload": {
            "shipmentId": f"SHIP-LOAD-{suffix}",
            "customer": "ABC Retail Load Test",
            "destination": "Sydney",
        },
    }

    request = Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": API_KEY,
            "X-Partner-Id": PARTNER_ID,
        },
    )

    started = time.perf_counter()

    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            status_code = response.status
            error = ""
    except HTTPError as exc:
        status_code = exc.code
        response_body = exc.read().decode("utf-8", errors="replace")
        error = f"HTTPError: {exc.reason}"
    except URLError as exc:
        status_code = 0
        response_body = ""
        error = f"URLError: {exc.reason}"
    except Exception as exc:
        status_code = 0
        response_body = ""
        error = f"{type(exc).__name__}: {exc}"

    duration_ms = round((time.perf_counter() - started) * 1000, 2)

    returned_correlation_id = ""
    returned_event_id = ""

    try:
        parsed_response = json.loads(response_body)
        returned_correlation_id = parsed_response.get("correlationId", "")
        returned_event_id = parsed_response.get("eventId", "")
    except json.JSONDecodeError:
        pass

    return {
        "sequence": sequence,
        "shipment_id": payload["payload"]["shipmentId"],
        "submitted_correlation_id": payload["correlationId"],
        "returned_correlation_id": returned_correlation_id,
        "returned_event_id": returned_event_id,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "error": error,
        "response_body": response_body,
    }


def main() -> None:
    if not API_BASE_URL:
        raise SystemExit("LOGISTICS_API_URL environment variable is missing.")

    if not API_KEY:
        raise SystemExit("LOGISTICS_API_KEY environment variable is missing.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    print("=" * 64)
    print("Controlled End-to-End Integration Load Test")
    print("=" * 64)
    print(f"Endpoint:       {ENDPOINT}")
    print(f"Partner:        {PARTNER_ID}")
    print(f"Requests:       {REQUEST_COUNT}")
    print(f"Concurrency:    {CONCURRENCY}")
    print(f"Run ID:         {RUN_ID}")
    print("=" * 64)

    test_started = time.perf_counter()
    results: list[dict] = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=CONCURRENCY
    ) as executor:
        future_map = {
            executor.submit(send_request, sequence): sequence
            for sequence in range(1, REQUEST_COUNT + 1)
        }

        completed = 0

        for future in concurrent.futures.as_completed(future_map):
            result = future.result()
            results.append(result)
            completed += 1

            print(
                f"[{completed:03d}/{REQUEST_COUNT}] "
                f"HTTP {result['status_code']} | "
                f"{result['duration_ms']:8.2f} ms | "
                f"{result['shipment_id']}"
            )

    elapsed_seconds = time.perf_counter() - test_started
    results.sort(key=lambda item: item["sequence"])

    accepted = sum(item["status_code"] == 202 for item in results)
    failed = REQUEST_COUNT - accepted
    durations = [item["duration_ms"] for item in results]
    status_counts: dict[int, int] = {}

    for item in results:
        status = item["status_code"]
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = {
        "run_id": RUN_ID,
        "endpoint": ENDPOINT,
        "partner_id": PARTNER_ID,
        "requests_sent": REQUEST_COUNT,
        "concurrency": CONCURRENCY,
        "accepted_202": accepted,
        "failed": failed,
        "acceptance_rate_percent": round(
            accepted / REQUEST_COUNT * 100, 2
        ),
        "elapsed_seconds": round(elapsed_seconds, 2),
        "average_requests_per_second": round(
            REQUEST_COUNT / elapsed_seconds, 2
        ),
        "minimum_duration_ms": min(durations),
        "average_duration_ms": round(statistics.mean(durations), 2),
        "median_duration_ms": round(statistics.median(durations), 2),
        "maximum_duration_ms": max(durations),
        "status_counts": status_counts,
    }

    csv_path = OUTPUT_DIR / "request-results.csv"
    json_path = OUTPUT_DIR / "summary.json"

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    with json_path.open("w", encoding="utf-8") as json_file:
        json.dump(summary, json_file, indent=2)

    print()
    print("=" * 64)
    print("Load Test Complete")
    print("=" * 64)
    print(f"Requests sent:       {REQUEST_COUNT}")
    print(f"Accepted (202):      {accepted}")
    print(f"Failed:              {failed}")
    print(f"Acceptance rate:     {summary['acceptance_rate_percent']}%")
    print(f"Elapsed time:        {summary['elapsed_seconds']} seconds")
    print(
        f"Average rate:        "
        f"{summary['average_requests_per_second']} requests/second"
    )
    print(f"Average latency:     {summary['average_duration_ms']} ms")
    print(f"Maximum latency:     {summary['maximum_duration_ms']} ms")
    print(f"Status distribution: {status_counts}")
    print(f"Results directory:   {OUTPUT_DIR.resolve()}")
    print("=" * 64)

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()