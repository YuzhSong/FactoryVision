import unittest

from modules.backend_client import BackendClient


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        page = params.get("page", 1) if params else 1
        return _FakeResponse(self.pages[page - 1])


class BackendClientTests(unittest.TestCase):
    def test_list_employees_reads_paginated_backend_response(self):
        client = BackendClient("http://backend/api", timeout_seconds=3)
        client.session = _FakeSession(
            [
                {"code": 200, "data": {"total": 3, "items": [{"id": 1}, {"id": 2}]}},
                {"code": 200, "data": {"total": 3, "items": [{"id": 3}]}},
            ]
        )

        employees = client.list_employees(page_size=2)

        self.assertEqual([employee["id"] for employee in employees], [1, 2, 3])
        self.assertEqual(len(client.session.calls), 2)
        self.assertEqual(client.session.calls[0]["params"]["status"], "active")
        self.assertEqual(client.session.calls[1]["params"]["page"], 2)


if __name__ == "__main__":
    unittest.main()
