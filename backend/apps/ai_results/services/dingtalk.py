"""
DingTalk robot notification client.

Usage (Django shell):
    from apps.ai_results.services.dingtalk import DingTalkNotifier

    notifier = DingTalkNotifier()
    notifier.send_alert(
        alert_title="未佩戴安全帽",
        level="高",
        content="检测到人员未佩戴安全帽",
        camera_name="1号车间摄像头",
        location="生产区域 A",
        responsible_name="张三",
        responsible_mobile="13800000000",
    )
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
import urllib.parse
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DingTalkNotificationError(Exception):
    pass


def _sign(secret: str) -> tuple[int, str]:
    timestamp = int(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    sign = urllib.parse.quote(sign, safe="")
    return timestamp, sign


class DingTalkNotifier:
    def __init__(self) -> None:
        self._enabled = settings.DINGTALK_ENABLED
        self._webhook = settings.DINGTALK_WEBHOOK
        self._secret = settings.DINGTALK_SECRET
        self._timeout = settings.DINGTALK_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        return self._enabled and bool(self._webhook)

    def send_markdown(
        self,
        title: str,
        text: str,
        at_mobiles: list[str] | None = None,
        at_all: bool = False,
    ) -> dict[str, Any]:
        if not self._enabled:
            logger.info("DingTalk notification disabled, skipping")
            return {"sent": False, "reason": "disabled"}

        if not self._webhook:
            logger.warning("DingTalk webhook not configured, skipping")
            return {"sent": False, "reason": "missing_webhook"}

        url = self._webhook
        if self._secret:
            timestamp, sign = _sign(self._secret)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}timestamp={timestamp}&sign={sign}"

        payload: dict[str, Any] = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text,
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all,
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("DingTalk request failed: %s", e)
            raise DingTalkNotificationError("Failed to send DingTalk notification") from e
        except ValueError as e:
            logger.error("DingTalk response JSON parse error: %s", e)
            raise DingTalkNotificationError("Invalid DingTalk response") from e

        if data.get("errcode") != 0:
            errmsg = data.get("errmsg", "unknown error")
            logger.error("DingTalk business error: errcode=%s errmsg=%s", data.get("errcode"), errmsg)
            raise DingTalkNotificationError(f"DingTalk returned error: {errmsg}")

        logger.info("DingTalk notification sent successfully")
        return {"sent": True, "response": data}

    def send_alert(
        self,
        *,
        alert_title: str,
        level: str,
        content: str,
        occurred_at: str | None = None,
        camera_name: str | None = None,
        location: str | None = None,
        responsible_name: str | None = None,
        responsible_mobile: str | None = None,
    ) -> dict[str, Any]:
        lines = ["### 🚨 FactoryVision 告警", ""]
        lines.append(f"- **告警级别：** {level}")
        lines.append(f"- **告警类型：** {alert_title}")
        if occurred_at:
            lines.append(f"- **发生时间：** {occurred_at}")
        if camera_name:
            lines.append(f"- **摄像头：** {camera_name}")
        if location:
            lines.append(f"- **位置：** {location}")
        if responsible_name:
            lines.append(f"- **责任人：** {responsible_name}")
        lines.append("")
        lines.append(f"> {content}")
        if responsible_mobile:
            lines.append("")
            lines.append(f"@{responsible_mobile} 请相关责任人及时处理。")

        at_mobiles = [responsible_mobile] if responsible_mobile else None

        return self.send_markdown(
            title=f"FactoryVision 告警 - {alert_title}",
            text="\n".join(lines),
            at_mobiles=at_mobiles,
        )
