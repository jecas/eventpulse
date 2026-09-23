import json
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"


def request(method, path, payload=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def wait_ready():
    for _ in range(40):
        try:
            status, _ = request("GET", "/health")
            if status == 200:
                return
        except (urllib.error.URLError, ConnectionResetError, TimeoutError):
            pass
        time.sleep(1)
    raise RuntimeError("EventPulse did not become ready")


def create_event(payload, correlation_id):
    status, body = request(
        "POST",
        "/api/v1/events",
        payload,
        {"X-Correlation-ID": correlation_id},
    )
    assert status == 202, body
    assert body["status"] == "queued"
    return body["event_id"]


def wait_for_status(event_id, expected, timeout=20):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        status, body = request("GET", f"/api/v1/events/{event_id}")
        assert status == 200, body
        last = body
        if body["status"] == expected:
            return body
        time.sleep(0.5)
    raise AssertionError(f"Expected {expected}, last response: {last}")


def main():
    wait_ready()

    success_id = create_event(
        {"event_type": "customer.notification", "payload": {"message": "hello"}},
        "e2e-success",
    )
    completed = wait_for_status(success_id, "completed")
    assert completed["attempts"] == 1

    retry_id = create_event(
        {"event_type": "customer.notification", "payload": {"mode": "fail_once"}},
        "e2e-retry",
    )
    retried = wait_for_status(retry_id, "completed")
    assert retried["attempts"] == 2

    failed_id = create_event(
        {"event_type": "customer.notification", "payload": {"mode": "always_fail"}},
        "e2e-failure",
    )
    failed = wait_for_status(failed_id, "failed")
    assert failed["attempts"] == 3

    print("EventPulse E2E tests passed.")


if __name__ == "__main__":
    main()
