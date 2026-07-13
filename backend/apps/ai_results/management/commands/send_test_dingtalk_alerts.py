"""
向钉钉真实发送「每种报警类型」各一条测试消息，用于联调验证。

走的是真实告警发送路径 DingTalkNotifier.send_alert，
因此消息里的告警类型会显示成中文（与线上真实告警一致）。

不访问数据库，可在迁移前运行。

用法:
    python manage.py send_test_dingtalk_alerts
    python manage.py send_test_dingtalk_alerts --recipient leader
    python manage.py send_test_dingtalk_alerts --type fall_detected
"""

from __future__ import annotations

import sys
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ai_results.services.dingtalk import (
    DingTalkNotifier,
    DingTalkNotificationError,
)

# 与 views._ALERT_TYPE_DISPLAY 保持一致的报警类型 -> 中文名。
ALERT_TYPE_DISPLAY = {
    "helmet_violation": "未佩戴安全帽",
    "region_intrusion": "区域闯入",
    "region_dwell": "区域滞留",
    "stranger_detected": "陌生人闯入",
    "fall_detected": "人员跌倒",
}

# 各类型的默认级别（与 views._default_level 的效果一致，仅用于展示）。
ALERT_TYPE_LEVEL = {
    "helmet_violation": "中",
    "region_intrusion": "中",
    "region_dwell": "高",
    "stranger_detected": "高",
    "fall_detected": "高",
}


def _mask_mobile(mobile: str) -> str:
    if len(mobile) == 11:
        return mobile[:3] + "****" + mobile[-4:]
    if mobile:
        return mobile[:3] + "****"
    return "(未设置)"


class Command(BaseCommand):
    help = "向钉钉真实发送每种报警类型各一条测试消息（验证类型触发与中文类型名）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--recipient",
            type=str,
            default="responsible",
            choices=["responsible", "leader"],
            help="使用哪个接收人（默认 responsible）",
        )
        parser.add_argument(
            "--type",
            type=str,
            default="",
            choices=list(ALERT_TYPE_DISPLAY.keys()),
            help="只发送指定的报警类型（默认发送全部类型）",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=1.0,
            help="每条消息之间的间隔秒数，避免触发钉钉限流（默认 1.0）",
        )

    def handle(self, *args, **options):
        if not settings.DINGTALK_ENABLED:
            self.stderr.write("ERROR: 钉钉通知未启用，请在 .env 设置 DINGTALK_ENABLED=True。")
            sys.exit(1)

        if not settings.DINGTALK_WEBHOOK:
            self.stderr.write("ERROR: DINGTALK_WEBHOOK 未配置。")
            sys.exit(1)

        recipient_type = options["recipient"]
        if recipient_type == "leader":
            name = settings.DINGTALK_LEADER_NAME or ""
            mobile = settings.DINGTALK_LEADER_MOBILE or ""
        else:
            name = settings.DINGTALK_RESPONSIBLE_NAME or ""
            mobile = settings.DINGTALK_RESPONSIBLE_MOBILE or ""

        only_type = options["type"]
        if only_type:
            types = {only_type: ALERT_TYPE_DISPLAY[only_type]}
        else:
            types = ALERT_TYPE_DISPLAY

        interval = options["interval"]
        now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        notifier = DingTalkNotifier()

        self.stdout.write(f"接收人类型: {recipient_type}")
        self.stdout.write(f"接收人姓名: {name or '(未设置)'}")
        self.stdout.write(f"接收人手机: {_mask_mobile(mobile) if mobile else '(未设置)'}")
        self.stdout.write(f"待发送类型数: {len(types)}")
        self.stdout.write("-" * 40)

        sent, failed = 0, 0
        for index, (event_type, chinese) in enumerate(types.items()):
            level = ALERT_TYPE_LEVEL.get(event_type, "中")
            try:
                notifier.send_alert(
                    alert_title=f"[测试] {chinese}",
                    level=level,
                    content=f"这是一条 {chinese}（{event_type}）的测试告警，非真实事件。",
                    occurred_at=now,
                    camera_name="测试摄像头",
                    location="测试区域",
                    responsible_name=name or None,
                    responsible_mobile=mobile or None,
                )
            except DingTalkNotificationError as e:
                failed += 1
                self.stderr.write(f"  [失败] {chinese} ({event_type}): {e}")
            else:
                sent += 1
                self.stdout.write(f"  [成功] {chinese} ({event_type})")

            # 最后一条之后不再等待。
            if index < len(types) - 1 and interval > 0:
                time.sleep(interval)

        self.stdout.write("-" * 40)
        self.stdout.write(f"完成: 成功 {sent} 条，失败 {failed} 条。")
        if failed:
            sys.exit(1)
