import unittest

from modules.backend_client import BackendClient


class _FakeResponse:
    """Fake requests response object for backend client tests."""

    def __init__(self, payload):
        """Store JSON payload for fake response."""
        self.payload = payload

    def raise_for_status(self):
        """Pretend HTTP status is successful."""
        return None

    def json(self):
        """Return stored JSON payload."""
        return self.payload


class _FakeSession:
    """Fake requests session with paginated GET responses."""

    def __init__(self, pages):
        """Store fake pages and request call history."""
        self.pages = pages
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None, verify=True):
        """Return fake page selected by params.page."""
        self.calls.append({"url": url, "params": params, "timeout": timeout, "verify": verify})
        page = params.get("page", 1) if params else 1
        return _FakeResponse(self.pages[page - 1])


class BackendClientTests(unittest.TestCase):
    """Test backend client helpers."""

    def test_list_employees_reads_paginated_backend_response(self):
        """Verify employee list pagination stops after short page."""
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
        self.assertTrue(client.session.calls[0]["verify"])

    def test_tls_verify_can_be_disabled(self):
        """Verify backend client can connect through IP endpoints with mismatched TLS names."""
        client = BackendClient("https://backend/api", tls_verify=False)
        client.session = _FakeSession([{"code": 200, "data": {"items": []}}])

        client.list_zones(camera_id=1)

        self.assertFalse(client.session.calls[0]["verify"])


if __name__ == "__main__":
    unittest.main()
