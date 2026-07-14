"""Local-only live verification for HTTP report -> database -> Channels WebSocket."""

import asyncio
import json
from datetime import datetime, timezone

import requests
import websockets


async def main():
    camera_id = 1
    ws_url = f"ws://127.0.0.1:8000/ws/realtime/{camera_id}/"
    payload = {
        "cameraId": camera_id,
        "frameId": "codex-region-dwell-live",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": [{
            "type": "ZONE_WARNING",
            "eventType": "region_dwell",
            "trackId": "codex-track-1",
            "regionId": 1,
            "regionName": "一号车间禁入区",
            "durationSeconds": 5.1,
            "confidence": 0.93,
            "level": "medium",
        }],
    }
    async with websockets.connect(ws_url) as socket:
        response = await asyncio.to_thread(
            requests.post,
            "http://127.0.0.1:8000/api/ai-results/report/",
            json=payload,
            headers={"X-AI-Service-Token": "factoryvision-local-e2e-token"},
            timeout=10,
        )
        message = await asyncio.wait_for(socket.recv(), timeout=10)
    print(json.dumps({
        "httpStatus": response.status_code,
        "httpBody": response.json(),
        "group": f"realtime_{camera_id}",
        "websocketMessage": json.loads(message),
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
