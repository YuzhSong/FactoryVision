import unittest

import numpy as np

from modules.frame_annotator import FrameAnnotator
from modules.zone_detector import ZoneDetector


def _zone(**overrides):
    zone = {
        "id": "danger-1", "name": "Danger Zone", "type": "restricted", "enabled": True,
        "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}, {"x": 0, "y": 100}],
    }
    zone.update(overrides)
    return zone


def _person(track_id="t-1", x=50, y=100):
    return {"type": "PERSON_DETECTION", "trackId": track_id, "footPoint": {"x": x, "y": y}, "confidence": 0.9}


class ZoneDetectorTests(unittest.TestCase):
    def test_point_inside_outside_and_boundary(self):
        detector = ZoneDetector([_zone()], min_stay_seconds=99)
        self.assertEqual(len(detector.detect_events(1, [_person(x=50, y=50)], "2026-07-11T10:00:00+08:00")), 1)
        self.assertEqual(detector.detect_events(1, [_person(x=150, y=50)], "2026-07-11T10:00:01+08:00"), [])
        boundary_detector = ZoneDetector([_zone()], min_stay_seconds=99)
        self.assertEqual(len(boundary_detector.detect_events(1, [_person(x=0, y=50)], "2026-07-11T10:00:02+08:00")), 1)

    def test_dwell_event_is_emitted_once_per_continuous_stay(self):
        detector = ZoneDetector([_zone(type="general")], min_stay_seconds=10)
        self.assertEqual(detector.detect_events(1, [_person()], "2026-07-11T10:00:00+08:00"), [])
        dwell = detector.detect_events(1, [_person()], "2026-07-11T10:00:10+08:00")
        self.assertEqual(dwell[0]["eventType"], "region_dwell")
        self.assertEqual(dwell[0]["durationSeconds"], 10.0)
        self.assertEqual(detector.detect_events(1, [_person()], "2026-07-11T10:00:11+08:00"), [])

    def test_leave_ttl_and_reentry_reset_the_state(self):
        detector = ZoneDetector([_zone(type="general")], min_stay_seconds=5, state_ttl_seconds=3)
        detector.detect_events(1, [_person()], "2026-07-11T10:00:00+08:00")
        detector.detect_events(1, [_person(x=150, y=50)], "2026-07-11T10:00:01+08:00")
        self.assertEqual(detector.state_count(), 1)
        detector.detect_events(1, [], "2026-07-11T10:00:04+08:00")
        self.assertEqual(detector.state_count(), 0)
        detector.detect_events(1, [_person()], "2026-07-11T10:00:05+08:00")
        detector.detect_events(1, [_person()], "2026-07-11T10:00:08+08:00")
        dwell = detector.detect_events(1, [_person()], "2026-07-11T10:00:10+08:00")
        self.assertEqual(dwell[0]["eventType"], "region_dwell")

    def test_camera_region_and_track_states_are_isolated(self):
        detector = ZoneDetector([_zone(type="general")], min_stay_seconds=5)
        detector.detect_events(1, [_person("t-1")], "2026-07-11T10:00:00+08:00")
        detector.detect_events(2, [_person("t-1")], "2026-07-11T10:00:01+08:00")
        detector.detect_events(1, [_person("t-2")], "2026-07-11T10:00:01+08:00")
        self.assertEqual(detector.state_count(), 3)
        dwell = detector.detect_events(1, [_person("t-1")], "2026-07-11T10:00:05+08:00")
        self.assertEqual(len(dwell), 1)
        self.assertEqual(dwell[0]["cameraId"], 1)
        self.assertEqual(dwell[0]["trackId"], "t-1")

    def test_normalized_backend_zone_points_use_frame_dimensions(self):
        detector = ZoneDetector([_zone(points=[{"x": 0.4, "y": 0.4}, {"x": 0.6, "y": 0.4}, {"x": 0.6, "y": 0.8}, {"x": 0.4, "y": 0.8}])], min_stay_seconds=99)
        events = detector.detect_events(1, [_person(x=50, y=70)], "2026-07-11T10:00:00+08:00", frame_shape=(100, 100, 3))
        self.assertEqual(events[0]["eventType"], "region_intrusion")

    def test_legacy_percentage_zone_points_use_frame_dimensions(self):
        detector = ZoneDetector([_zone(points=[{"x": 40, "y": 40}, {"x": 60, "y": 40}, {"x": 60, "y": 80}, {"x": 40, "y": 80}])], min_stay_seconds=99)
        events = detector.detect_events(1, [_person(x=50, y=70)], "2026-07-11T10:00:00+08:00", frame_shape=(100, 100, 3))
        self.assertEqual(events[0]["eventType"], "region_intrusion")

    def test_disabled_region_does_not_create_or_retain_state(self):
        detector = ZoneDetector([_zone(enabled=False)])
        self.assertEqual(detector.detect_events(1, [_person()], "2026-07-11T10:00:00+08:00"), [])
        self.assertEqual(detector.state_count(), 0)

    def test_region_and_person_helmet_boxes_render_together(self):
        frame = np.zeros((120, 120, 3), dtype=np.uint8)
        zones = [_zone()]
        results = [
            {"type": "ZONE_WARNING", "regionId": "danger-1", "durationSeconds": 10},
            {"type": "PERSON_DETECTION", "trackId": "t-1", "bbox": {"x1": 20, "y1": 20, "x2": 80, "y2": 100}},
            {"type": "HELMET_DETECTION", "helmetStatus": "helmet", "bbox": {"x1": 35, "y1": 25, "x2": 60, "y2": 45}},
        ]
        annotated = FrameAnnotator().draw_zones(frame, zones, results)
        annotated = FrameAnnotator().draw_results(annotated, results)
        self.assertEqual(annotated.shape, frame.shape)
        self.assertGreater(int(annotated.sum()), 0)


if __name__ == "__main__":
    unittest.main()
