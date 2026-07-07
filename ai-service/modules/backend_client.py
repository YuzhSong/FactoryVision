import requests


class BackendClient:
    """Call backend APIs for cameras, employees, zones, and AI reports."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5,
        token: str = "",
        camera_list_path: str = "/cameras/list/",
        employee_list_path: str = "/employees/list/",
        face_library_path: str = "",
        zone_list_path: str = "/zones/list/",
        ai_report_path: str = "/ai-results/report/",
    ):
        """Initialize backend client with base URL, timeout, token, and API paths."""
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.camera_list_path = camera_list_path
        self.employee_list_path = employee_list_path
        self.face_library_path = face_library_path
        self.zone_list_path = zone_list_path
        self.ai_report_path = ai_report_path
        self.session = requests.Session()

        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def list_cameras(self, status: str | None = "online"):
        """List cameras by status, defaulting to online cameras."""
        params = {"status": status} if status else None
        response_json = self.get_json(self.camera_list_path, params=params)
        return _extract_items(response_json)

    def find_camera(self, camera_id, status: str | None = None):
        """Find one camera by camera_id, optionally filtered by status."""
        for camera in self.list_cameras(status=status):
            if str(camera.get("id")) == str(camera_id):
                return camera
        return None

    def list_employees(self, status: str | None = "active", page_size: int = 200, max_pages: int = 20):
        """List employees with pagination using status, page_size, and max_pages."""
        employees = []

        for page in range(1, max_pages + 1):
            params = {"page": page, "pageSize": page_size}

            if status:
                params["status"] = status

            response_json = self.get_json(self.employee_list_path, params=params)
            items = _extract_items(response_json)
            employees.extend(items)

            if len(items) < page_size:
                break

        return employees

    def list_face_records(self, status: str | None = "active"):
        """List face records, falling back to employee records when needed."""
        if self.face_library_path:
            params = {"status": status} if status else None
            response_json = self.get_json(self.face_library_path, params=params)
            items = _extract_items(response_json)

            if items:
                return items

        return self.list_employees(status=status)

    def list_zones(self, camera_id):
        """List warning zones for one camera_id."""
        if not camera_id:
            return []

        response_json = self.get_json(self.zone_list_path, params={"cameraId": camera_id})
        return _extract_items(response_json)

    def report_ai_results(self, payload: dict):
        """Post one AI report payload to the backend report endpoint."""
        response = self.session.post(
            self._build_url(self.ai_report_path),
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def get_json(self, path: str, params: dict | None = None):
        """Send GET request to path with params and return parsed JSON."""
        response = self.session.get(
            self._build_url(path),
            params=params,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _build_url(self, path: str):
        """Build absolute backend URL from a relative API path."""
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized}"


def _extract_items(response_json):
    """Extract list items from common backend response shapes."""
    payload = response_json.get("data", response_json) if isinstance(response_json, dict) else response_json

    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return []

    for key in ("items", "results", "records", "faces", "employees", "cameras", "zones"):
        value = payload.get(key)
        if isinstance(value, list):
            return value

    if payload.get("status") == "placeholder":
        return []

    return []
