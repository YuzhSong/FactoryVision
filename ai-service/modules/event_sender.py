import requests


class EventSender:
    def __init__(self, backend_api_base_url: str, timeout: int = 5):
        self.backend_api_base_url = backend_api_base_url.rstrip("/")
        self.timeout = timeout

    def send_detection_result(self, endpoint: str, payload: dict):
        url = self._build_url(endpoint)
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def report_ai_results(self, payload: dict):
        self._validate_payload(payload)
        return self.send_detection_result("/ai-results/report/", payload)

    def _build_url(self, endpoint: str):
        normalized_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{self.backend_api_base_url}{normalized_endpoint}"

    def _validate_payload(self, payload: dict):
        required_fields = ["cameraId", "frameId", "timestamp", "results"]
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            raise ValueError(f"Missing required AI report fields: {', '.join(missing_fields)}")
        if not isinstance(payload.get("results"), list):
            raise ValueError("AI report field 'results' must be a list")
