from copy import deepcopy
from datetime import datetime, timezone
import threading


class RuntimeCache:
    """Thread-safe in-memory cache for backend bootstrap data."""

    def __init__(self):
        self._lock = threading.RLock()
        self._version = None
        self._loaded_at = None
        self._last_error = None
        self._cameras = []
        self._zones_by_camera = {}
        self._settings = {}

    def load_bootstrap(self, payload: dict | None):
        """Load cameras, zones, and settings from a backend bootstrap payload."""
        payload = payload or {}
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            data = {}

        with self._lock:
            self._version = data.get("version") or payload.get("version") or _now()
            self._loaded_at = _now()
            self._last_error = None
            if isinstance(data.get("cameras"), list):
                self._cameras = deepcopy(data["cameras"])
            if isinstance(data.get("zones"), list):
                self._zones_by_camera = _group_zones_by_camera(data["zones"])
            if isinstance(data.get("settings"), dict):
                self._settings = deepcopy(data["settings"])
            return self.status()

    def set_error(self, error):
        """Record the latest cache refresh error without failing service startup."""
        with self._lock:
            self._last_error = str(error)
            return self.status()

    def set_cameras(self, cameras, version=None):
        """Replace cached camera records."""
        with self._lock:
            self._cameras = deepcopy(cameras or [])
            self._version = version or self._version or _now()
            self._loaded_at = _now()
            self._last_error = None
            return self.status()

    def set_zones(self, zones, camera_id=None, version=None):
        """Replace cached zones globally or for one camera."""
        with self._lock:
            if camera_id not in (None, ""):
                self._zones_by_camera[str(camera_id)] = deepcopy(zones or [])
            else:
                self._zones_by_camera = _group_zones_by_camera(zones or [])
            self._version = version or self._version or _now()
            self._loaded_at = _now()
            self._last_error = None
            return self.status()

    def find_camera(self, camera_id):
        """Return one cached camera by id."""
        if camera_id in (None, ""):
            return None
        with self._lock:
            for camera in self._cameras:
                if str(camera.get("id")) == str(camera_id) or str(camera.get("cameraId")) == str(camera_id):
                    return deepcopy(camera)
        return None

    def camera_ids(self):
        """Return cached camera ids."""
        with self._lock:
            ids = []
            for camera in self._cameras:
                camera_id = camera.get("id", camera.get("cameraId"))
                if camera_id not in (None, ""):
                    ids.append(camera_id)
            return ids

    def get_zones(self, camera_id):
        """Return cached zones for one camera."""
        if camera_id in (None, ""):
            return []
        with self._lock:
            return deepcopy(self._zones_by_camera.get(str(camera_id), []))

    def status(self):
        """Return a serializable cache status snapshot."""
        with self._lock:
            return {
                "cacheReady": bool(self._loaded_at),
                "version": self._version,
                "loadedAt": self._loaded_at,
                "lastError": self._last_error,
                "cameraCount": len(self._cameras),
                "zoneCount": sum(len(zones) for zones in self._zones_by_camera.values()),
                "settingsKeys": sorted(self._settings.keys()),
            }


def _group_zones_by_camera(zones):
    grouped = {}
    for zone in zones or []:
        if not isinstance(zone, dict):
            continue
        camera_id = zone.get("cameraId", zone.get("camera_id"))
        if camera_id in (None, ""):
            continue
        grouped.setdefault(str(camera_id), []).append(deepcopy(zone))
    return grouped


def _now():
    return datetime.now(timezone.utc).astimezone().isoformat()
