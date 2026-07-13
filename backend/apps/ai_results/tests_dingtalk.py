"""
钉钉报警模块测试。

覆盖：
- _should_create_alert：哪些事件类型会触发钉钉通知。
- _alert_type_display：告警类型的中文展示名映射（含未知类型回退）。
- DingTalkNotifier.send_markdown / send_alert：发送开关、加签、错误处理、文案。
- _notify_dingtalk_alert / _escalate_alert：每种报警类型都能触发钉钉，
  且消息内容带上对应的中文告警类型。

所有用例均 mock 掉 requests.post，不发送真实网络请求。
"""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai_results import views
from apps.ai_results.models import Alert
from apps.ai_results.services.dingtalk import (
    DingTalkNotifier,
    DingTalkNotificationError,
)
from apps.cameras.models import Camera
from apps.events.models import Event


# _normalize_event_type 归一化后、会触发钉钉通知的全部报警类型。
ALERT_TYPES = {
    "helmet_violation": "未佩戴安全帽",
    "region_intrusion": "区域闯入",
    "region_dwell": "区域滞留",
    "stranger_detected": "陌生人闯入",
    "fall_detected": "人员跌倒",
}

# 明确不应触发钉钉的类型。
NON_ALERT_TYPES = ["face_recognized", "person", "", "unknown_type"]


class ShouldCreateAlertTests(TestCase):
    """触发判断：报警类型返回 True，其余返回 False。"""

    def test_all_alert_types_trigger(self):
        for event_type in ALERT_TYPES:
            with self.subTest(event_type=event_type):
                self.assertTrue(views._should_create_alert(event_type))

    def test_non_alert_types_do_not_trigger(self):
        for event_type in NON_ALERT_TYPES:
            with self.subTest(event_type=event_type):
                self.assertFalse(views._should_create_alert(event_type))

    def test_trigger_set_matches_expected(self):
        self.assertEqual(views.ALERT_TRIGGER_TYPES, set(ALERT_TYPES))


class AlertTypeDisplayTests(TestCase):
    """告警类型中文名映射。"""

    def _make_alert(self, event_type: str, title: str = "Fallback Title") -> Alert:
        return Alert(event_type=event_type, title=title, level="high")

    def test_known_types_map_to_chinese(self):
        for event_type, chinese in ALERT_TYPES.items():
            with self.subTest(event_type=event_type):
                alert = self._make_alert(event_type)
                self.assertEqual(views._alert_type_display(alert), chinese)

    def test_unknown_type_falls_back_to_title(self):
        alert = self._make_alert("some_new_type", title="Some New Type")
        self.assertEqual(views._alert_type_display(alert), "Some New Type")


class SendMarkdownTests(TestCase):
    """DingTalkNotifier.send_markdown 的开关、加签与错误处理。"""

    @override_settings(DINGTALK_ENABLED=False)
    def test_disabled_skips_sending(self):
        with mock.patch("apps.ai_results.services.dingtalk.requests.post") as post:
            result = DingTalkNotifier().send_markdown("t", "body")
        self.assertEqual(result, {"sent": False, "reason": "disabled"})
        post.assert_not_called()

    @override_settings(DINGTALK_ENABLED=True, DINGTALK_WEBHOOK="")
    def test_missing_webhook_skips_sending(self):
        with mock.patch("apps.ai_results.services.dingtalk.requests.post") as post:
            result = DingTalkNotifier().send_markdown("t", "body")
        self.assertEqual(result, {"sent": False, "reason": "missing_webhook"})
        post.assert_not_called()

    @override_settings(
        DINGTALK_ENABLED=True,
        DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=abc",
        DINGTALK_SECRET="",
    )
    def test_success_posts_markdown_payload(self):
        with mock.patch("apps.ai_results.services.dingtalk.requests.post") as post:
            post.return_value = mock.Mock(
                raise_for_status=mock.Mock(),
                json=mock.Mock(return_value={"errcode": 0, "errmsg": "ok"}),
            )
            result = DingTalkNotifier().send_markdown(
                "标题", "正文", at_mobiles=["13800000000"]
            )

        self.assertTrue(result["sent"])
        post.assert_called_once()
        _, kwargs = post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["msgtype"], "markdown")
        self.assertEqual(payload["markdown"]["title"], "标题")
        self.assertEqual(payload["markdown"]["text"], "正文")
        self.assertEqual(payload["at"]["atMobiles"], ["13800000000"])

    @override_settings(
        DINGTALK_ENABLED=True,
        DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=abc",
        DINGTALK_SECRET="secret-value",
    )
    def test_secret_appends_timestamp_and_sign(self):
        with mock.patch("apps.ai_results.services.dingtalk.requests.post") as post:
            post.return_value = mock.Mock(
                raise_for_status=mock.Mock(),
                json=mock.Mock(return_value={"errcode": 0}),
            )
            DingTalkNotifier().send_markdown("t", "body")

        called_url = post.call_args[0][0]
        self.assertIn("timestamp=", called_url)
        self.assertIn("sign=", called_url)

    @override_settings(
        DINGTALK_ENABLED=True,
        DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=abc",
        DINGTALK_SECRET="",
    )
    def test_business_error_raises(self):
        with mock.patch("apps.ai_results.services.dingtalk.requests.post") as post:
            post.return_value = mock.Mock(
                raise_for_status=mock.Mock(),
                json=mock.Mock(return_value={"errcode": 130101, "errmsg": "限流"}),
            )
            with self.assertRaises(DingTalkNotificationError):
                DingTalkNotifier().send_markdown("t", "body")


@override_settings(
    DINGTALK_ENABLED=True,
    DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=abc",
    DINGTALK_SECRET="",
    DINGTALK_RESPONSIBLE_NAME="张三",
    DINGTALK_RESPONSIBLE_MOBILE="13800000000",
    DINGTALK_LEADER_NAME="李四",
    DINGTALK_LEADER_MOBILE="13900000000",
    DINGTALK_ESCALATION_SECONDS=0,  # 关闭定时器，避免测试起后台线程
)
class NotifyAlertByTypeTests(TestCase):
    """每种报警类型都触发钉钉，且消息内容带上对应中文告警类型。"""

    def setUp(self):
        self.camera = Camera.objects.create(
            name="1号车间",
            code="CAM-A",
            stream_url="rtmp://example/live/a",
            processed_stream_url="rtmp://example/live/a_ai",
            status=Camera.Status.ONLINE,
            location="生产区域 A",
        )

    def _make_alert(self, event_type: str) -> Alert:
        event = Event.objects.create(
            camera=self.camera,
            event_type=event_type,
            occurred_at=timezone.now(),
            severity="high",
        )
        return Alert.objects.create(
            event=event,
            camera=self.camera,
            event_type=event_type,
            level="high",
            title=views._alert_title(event_type),
            description=f"desc-{event_type}",
            occurred_at=event.occurred_at,
        )

    def test_every_alert_type_triggers_dingtalk(self):
        for event_type in ALERT_TYPES:
            with self.subTest(event_type=event_type):
                alert = self._make_alert(event_type)
                with mock.patch.object(
                    views.DingTalkNotifier, "send_alert"
                ) as send_alert:
                    views._notify_dingtalk_alert(alert)
                send_alert.assert_called_once()

    def test_alert_title_uses_chinese_type_name(self):
        for event_type, chinese in ALERT_TYPES.items():
            with self.subTest(event_type=event_type):
                alert = self._make_alert(event_type)
                with mock.patch.object(
                    views.DingTalkNotifier, "send_alert"
                ) as send_alert:
                    views._notify_dingtalk_alert(alert)
                kwargs = send_alert.call_args.kwargs
                self.assertEqual(kwargs["alert_title"], chinese)

    def test_alert_time_is_formatted_to_seconds(self):
        alert = self._make_alert("region_intrusion")
        alert.occurred_at = timezone.datetime(
            2026,
            7,
            13,
            19,
            35,
            50,
            366943,
            tzinfo=timezone.get_current_timezone(),
        )
        alert.save(update_fields=["occurred_at"])

        with mock.patch.object(views.DingTalkNotifier, "send_alert") as send_alert:
            views._notify_dingtalk_alert(alert)

        occurred_at = send_alert.call_args.kwargs["occurred_at"]
        self.assertEqual(occurred_at, "2026-07-13 19:35:50")
        self.assertNotIn("T", occurred_at)
        self.assertNotIn("+", occurred_at)

    def test_message_text_contains_chinese_type(self):
        """端到端到 payload：中文类型名真正出现在钉钉 markdown 文本里。"""
        for event_type, chinese in ALERT_TYPES.items():
            with self.subTest(event_type=event_type):
                alert = self._make_alert(event_type)
                with mock.patch(
                    "apps.ai_results.services.dingtalk.requests.post"
                ) as post:
                    post.return_value = mock.Mock(
                        raise_for_status=mock.Mock(),
                        json=mock.Mock(return_value={"errcode": 0}),
                    )
                    views._notify_dingtalk_alert(alert)
                text = post.call_args.kwargs["json"]["markdown"]["text"]
                self.assertIn(chinese, text)

    def test_escalation_uses_chinese_type_name(self):
        for event_type, chinese in ALERT_TYPES.items():
            with self.subTest(event_type=event_type):
                alert = self._make_alert(event_type)
                with mock.patch.object(
                    views.DingTalkNotifier, "send_alert"
                ) as send_alert:
                    views._escalate_alert(alert.id)
                kwargs = send_alert.call_args.kwargs
                self.assertEqual(kwargs["alert_title"], f"[告警升级] {chinese}")

    def test_escalation_skipped_when_alert_handled(self):
        alert = self._make_alert("fall_detected")
        alert.status = Alert.Status.PROCESSING
        alert.save(update_fields=["status"])
        with mock.patch.object(views.DingTalkNotifier, "send_alert") as send_alert:
            views._escalate_alert(alert.id)
        send_alert.assert_not_called()
