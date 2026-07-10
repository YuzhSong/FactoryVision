from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ai_results.models import Alert
from apps.cameras.models import Camera
from apps.employees.models import Employee
from apps.events.models import Event
from apps.users.models import User
from apps.zones.models import Zone


class Command(BaseCommand):
    help = "Create idempotent local development data in the configured database."

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"role": User.Role.ADMIN, "is_staff": True, "is_superuser": True},
        )
        admin.role = User.Role.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("admin123456")
        admin.save()

        entrance, _ = Camera.objects.update_or_create(
            code="CAM-ENTRANCE-001",
            defaults={
                "name": "一号车间入口摄像头",
                "stream_url": "rtmp://127.0.0.1/live/entrance",
                "processed_stream_url": "rtmp://127.0.0.1/live/entrance_ai",
                "location": "一号车间入口",
                "status": Camera.Status.ONLINE,
                "enabled": True,
            },
        )
        webrtc, _ = Camera.objects.update_or_create(
            code="CAM-WEBRTC-001",
            defaults={
                "name": "WebRTC 测试摄像头",
                "stream_url": "webrtc://127.0.0.1/live/test",
                "processed_stream_url": "webrtc://127.0.0.1/live/test_ai",
                "location": "本地测试区",
                "status": Camera.Status.ONLINE,
                "enabled": True,
            },
        )

        for employee_no, name, department, position in (
            ("EMP-001", "张三", "生产部", "操作员"),
            ("EMP-002", "李四", "安全部", "安全员"),
            ("EMP-003", "王五", "设备部", "设备维护"),
        ):
            Employee.objects.update_or_create(
                employee_no=employee_no,
                defaults={
                    "name": name,
                    "department": department,
                    "position": position,
                    "status": Employee.Status.ACTIVE,
                },
            )

        self._seed_zone(
            entrance,
            "一号车间禁入区",
            Zone.ZoneType.RESTRICTED,
            [{"x": 8, "y": 12}, {"x": 42, "y": 12}, {"x": 42, "y": 78}, {"x": 8, "y": 78}],
        )
        self._seed_zone(
            webrtc,
            "设备维护区域",
            Zone.ZoneType.DANGER,
            [{"x": 55, "y": 20}, {"x": 92, "y": 20}, {"x": 92, "y": 85}, {"x": 55, "y": 85}],
        )

        now = timezone.now()
        event_definitions = (
            ("seed-event-01", entrance, "NO_HELMET", "high", "未佩戴安全帽"),
            ("seed-event-02", entrance, "ZONE_INTRUSION", "high", "禁区闯入"),
            ("seed-event-03", webrtc, "STRANGER_DETECTED", "high", "陌生人检测"),
            ("seed-event-04", entrance, "FALL_DETECTED", "high", "摔倒/异常行为"),
            ("seed-event-05", webrtc, "PERSON_DETECTION", "info", "普通人员检测"),
            ("seed-event-06", entrance, "HELMET_WARNING", "medium", "安全帽提示"),
            ("seed-event-07", webrtc, "RUNNING_ALERT", "medium", "奔跑行为提示"),
            ("seed-event-08", entrance, "FACE_RESULT", "info", "普通识别提示"),
        )
        events = {}
        for index, (frame_id, camera, event_type, severity, description) in enumerate(event_definitions):
            event, _ = Event.objects.update_or_create(
                frame_id=frame_id,
                defaults={
                    "camera": camera,
                    "camera_identifier": camera.code,
                    "event_type": event_type,
                    "source": Event.Source.AI_SERVICE,
                    "severity": severity,
                    "status": Event.Status.NEW,
                    "occurred_at": now - timedelta(minutes=index * 5),
                    "track_id": f"seed-track-{index + 1}",
                    "bbox": {"x": 10 + index, "y": 20, "w": 80, "h": 160},
                    "confidence": 0.75 + index * 0.01,
                    "payload": {"seed": True, "description": description},
                },
            )
            events[frame_id] = event

        for frame_id, level, title in (
            ("seed-event-01", "high", "未佩戴安全帽"),
            ("seed-event-02", "high", "禁区闯入"),
            ("seed-event-03", "high", "陌生人检测"),
            ("seed-event-04", "high", "摔倒/异常行为"),
            ("seed-event-06", "medium", "安全帽提示"),
        ):
            event = events[frame_id]
            Alert.objects.update_or_create(
                event=event,
                defaults={
                    "camera": event.camera,
                    "event_type": event.event_type,
                    "level": level,
                    "status": Alert.Status.PENDING,
                    "title": title,
                    "description": event.payload["description"],
                    "occurred_at": event.occurred_at,
                },
            )

        self.stdout.write(self.style.SUCCESS("Local development data is ready."))

    @staticmethod
    def _seed_zone(camera, name, zone_type, points):
        Zone.objects.update_or_create(
            camera=camera,
            name=name,
            defaults={"type": zone_type, "points": points, "enabled": True},
        )
