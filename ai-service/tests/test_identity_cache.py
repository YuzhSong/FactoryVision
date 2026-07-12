import unittest

from modules.identity_cache import FaceIdentityCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FaceIdentityCacheTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.cache = FaceIdentityCache(5, 1, 3, clock=self.clock)

    def test_cache_isolated_and_expires(self):
        self.cache.put(1, {"trackId": "t1", "matched": True, "employeeId": 7, "name": "Worker", "similarity": .9, "faceBox": {}})
        self.assertEqual(self.cache.get(1, "t1")["employeeId"], 7)
        self.assertIsNone(self.cache.get(2, "t1"))
        self.assertIsNone(self.cache.get(1, "t2"))
        self.clock.now = 5
        self.assertIsNone(self.cache.get(1, "t1"))

    def test_unknown_retries_earlier_and_library_refresh_invalidates(self):
        self.cache.put(1, {"trackId": "t1", "matched": False, "similarity": .2})
        self.clock.now = 1
        self.assertIsNone(self.cache.get(1, "t1"))
        self.cache.put(1, {"trackId": "t1", "matched": True, "employeeId": 7})
        self.cache.invalidate_library()
        self.assertIsNone(self.cache.get(1, "t1"))

    def test_missing_track_is_purged_after_track_ttl(self):
        self.cache.put(1, {"trackId": "t1", "matched": True, "employeeId": 7})
        self.clock.now = 4
        self.cache.purge_missing(1, [])
        self.assertIsNone(self.cache.get(1, "t1"))

    def test_reappearing_track_id_does_not_inherit_identity(self):
        self.cache.put(1, {"trackId": "t1", "matched": True, "employeeId": 7})
        self.cache.purge_missing(1, [])
        self.clock.now = 1
        self.cache.purge_missing(1, ["t1"])
        self.assertIsNone(self.cache.get(1, "t1"))


if __name__ == "__main__":
    unittest.main()
