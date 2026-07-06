class EventSender:
    def __init__(self, backend_api_base_url: str):
        self.backend_api_base_url = backend_api_base_url

    def send_detection_result(self, endpoint: str, payload: dict):
        raise NotImplementedError("Backend reporting will be implemented in a later stage.")
