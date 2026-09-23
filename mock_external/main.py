from fastapi import FastAPI, HTTPException

app = FastAPI(title="EventPulse Mock External Service")
_attempts: dict[str, int] = {}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process")
async def process(payload: dict) -> dict[str, str]:
    event_id = str(payload["event_id"])
    mode = payload.get("payload", {}).get("mode")

    if mode == "always_fail":
        raise HTTPException(status_code=503, detail="Simulated provider failure")

    if mode == "fail_once":
        count = _attempts.get(event_id, 0)
        _attempts[event_id] = count + 1
        if count == 0:
            raise HTTPException(status_code=503, detail="Simulated transient failure")

    return {"status": "processed", "event_id": event_id}
