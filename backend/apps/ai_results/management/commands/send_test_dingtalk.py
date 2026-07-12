"""
Management command to manually send a test DingTalk message.

Does NOT access any database table, so it can be run before migration.

Usage:
    python manage.py send_test_dingtalk
    python manage.py send_test_dingtalk --recipient leader
    python manage.py send_test_dingtalk --title "联调测试" --content "验证消息送达"
"""

from __future__ import annotations

import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ai_results.services.dingtalk import DingTalkNotifier, DingTalkNotificationError


def _mask_mobile(mobile: str) -> str:
    if len(mobile) == 11:
        return mobile[:3] + "****" + mobile[-4:]
    if mobile:
        return mobile[:3] + "****"
    return "(未设置)"


class Command(BaseCommand):
    help = "Send a test DingTalk message to verify webhook, secret, and @mention."

    def add_arguments(self, parser):
        parser.add_argument(
            "--recipient",
            type=str,
            default="responsible",
            choices=["responsible", "leader"],
            help="Which recipient to use (default: responsible)",
        )
        parser.add_argument(
            "--title",
            type=str,
            default="",
            help="Custom title for the test message",
        )
        parser.add_argument(
            "--content",
            type=str,
            default="",
            help="Custom content for the test message",
        )

    def handle(self, *args, **options):
        if not settings.DINGTALK_ENABLED:
            self.stderr.write("ERROR: DingTalk notification is disabled. Set DINGTALK_ENABLED=True.")
            sys.exit(1)

        if not settings.DINGTALK_WEBHOOK:
            self.stderr.write("ERROR: DINGTALK_WEBHOOK is missing.")
            sys.exit(1)

        recipient_type = options["recipient"]
        if recipient_type == "leader":
            name = settings.DINGTALK_LEADER_NAME or ""
            mobile = settings.DINGTALK_LEADER_MOBILE or ""
        else:
            name = settings.DINGTALK_RESPONSIBLE_NAME or ""
            mobile = settings.DINGTALK_RESPONSIBLE_MOBILE or ""

        title = options["title"] or "FactoryVision 钉钉通知测试"
        custom_content = options["content"] or "这是一条手动发送测试消息，不是真实告警。"

        now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"### 🧪 {title}",
            "",
            f"- **告警级别：** 测试",
            f"- **接收人：** {name or '(未设置)'}",
            f"- **发送时间：** {now}",
            "",
            f"> {custom_content}",
        ]
        if mobile:
            lines.append("")
            lines.append(f"@{mobile} 测试消息提醒。")

        try:
            result = DingTalkNotifier().send_markdown(
                title=title,
                text="\n".join(lines),
                at_mobiles=[mobile] if mobile else None,
            )
        except DingTalkNotificationError as e:
            self.stderr.write(f"ERROR: DingTalk test message failed: {e}")
            sys.exit(1)

        self.stdout.write("DingTalk test message sent successfully.")
        self.stdout.write(f"  Recipient type: {recipient_type}")
        self.stdout.write(f"  Recipient name: {name or '(未设置)'}")
        self.stdout.write(f"  Recipient mobile: {_mask_mobile(mobile) if mobile else '(未设置)'}")
        self.stdout.write(f"  Response: {result}")
