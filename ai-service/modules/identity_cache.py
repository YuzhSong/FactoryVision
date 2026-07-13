import time
from datetime import datetime, timezone


class FaceIdentityCache:
    """Short-lived face identity cache isolated by camera and tracker identity."""

    def __init__(self, ttl_seconds=5.0, unknown_ttl_seconds=1.0, track_ttl_seconds=10.0, clock=None):
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self.unknown_ttl_seconds = max(0.0, float(unknown_ttl_seconds))
        self.track_ttl_seconds = max(0.1, float(track_ttl_seconds))
        self.clock = clock or time.monotonic
        self._items = {}
        self.generation = 0

    def put(self, camera_id, result):
        track_id = result.get("trackId")
        if camera_id in (None, "") or track_id in (None, ""):
            return None
        now = self.clock()
        matched = result.get("matched") is True
        ttl = self.ttl_seconds if matched else self.unknown_ttl_seconds
        item = {
            "type": "FACE_RESULT",
            "trackId": str(track_id),
            "employeeId": result.get("employeeId"),
            "employeeName": result.get("name") or result.get("employeeName") or "Unknown",
            "name": result.get("name") or result.get("employeeName") or "Unknown",
            "matched": matched,
            "similarity": result.get("similarity", 0.0),
            "faceBox": result.get("faceBox"),
            "recognizedAt": _iso_now(),
            "expiresAt": now + ttl,
            "lastSeenAt": now,
            "missingSince": None,
            "generation": self.generation,
        }
        self._items[(str(camera_id), str(track_id))] = item
        return dict(item)

    def get(self, camera_id, track_id):
        key = (str(camera_id), str(track_id))
        item = self._items.get(key)
        if not item:
            return None
        now = self.clock()
        if item["generation"] != self.generation or now >= item["expiresAt"]:
            self._items.pop(key, None)
            return None
        item["lastSeenAt"] = now
        return dict(item)

    def results_for_tracks(self, camera_id, track_ids):
        return [item for track_id in track_ids if (item := self.get(camera_id, track_id)) is not None]

    def purge_missing(self, camera_id, visible_track_ids):
        now = self.clock()
        visible = {str(value) for value in visible_track_ids}
        for key, item in list(self._items.items()):
            if key[0] != str(camera_id):
                continue
            if key[1] in visible:
                if item.get("missingSince") is not None:
                    # A tracker id that disappeared and reappeared is a new continuity.
                    self._items.pop(key, None)
                continue
            item["missingSince"] = item.get("missingSince") or now
            if now - item["lastSeenAt"] > self.track_ttl_seconds:
                self._items.pop(key, None)

    def invalidate_library(self):
        self.generation += 1
        self._items.clear()

    def clear(self):
        self._items.clear()


def _iso_now():
    return datetime.now(timezone.utc).astimezone().isoformat()
