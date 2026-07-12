"""Local live verification for AIService FIFO -> Backend -> WebSocket."""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import websockets

os.environ["BACKEND_API_TOKEN"] = "factoryvision-local-e2e-token"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import backend_client, processed_stream_service  # noqa: E402
from modules.zone_detector import ZoneDetector  # noqa: E402


async def main():
    zones = backend_client.list_zones(1)
    detector = ZoneDetector(zones, min_stay_seconds=5, state_ttl_seconds=2)
    entered_at = datetime.now(timezone.utc)
    detection = {"trackId": "codex-track-fifo", "confidence": .94, "bbox": {"x1": 10, "y1": 5, "x2": 20, "y2": 20}}
    early = detector.detect_events(1, [detection], entered_at.isoformat(), frame_shape=(100, 100, 3))
    before_five = []
    for seconds in (1, 2, 3, 4, 4.9):
        before_five = detector.detect_events(1, [detection], (entered_at + timedelta(seconds=seconds)).isoformat(), frame_shape=(100, 100, 3))
    at_five = detector.detect_events(1, [detection], (entered_at + timedelta(seconds=5.2)).isoformat(), frame_shape=(100, 100, 3))
    dwell = next(item for item in at_five if item.get("eventType") == "region_dwell")
    payload = {
        "cameraId": 1,
        "frameId": "codex-region-dwell-fifo",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": [dwell],
    }
    before = processed_stream_service.status()
    async with websockets.connect("ws://127.0.0.1:8000/ws/realtime/1/") as socket:
        queued = processed_stream_service._enqueue_ai_report(payload)
        message = json.loads(await asyncio.wait_for(socket.recv(), timeout=10))
        deadline = time.monotonic() + 10
        while processed_stream_service.status()["reported_events"] <= before["reported_events"] and time.monotonic() < deadline:
            await asyncio.sleep(0.05)
    print(json.dumps({
        "queued": queued,
        "loadedZoneCount": len(zones),
        "earlyEventTypes": [item.get("eventType") for item in early],
        "beforeFiveHasDwell": any(item.get("eventType") == "region_dwell" for item in before_five),
        "generatedDwell": dwell,
        "before": before,
        "after": processed_stream_service.status(),
        "group": "realtime_1",
        "websocketMessage": message,
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
