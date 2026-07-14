from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
import os

from django.conf import settings
from django.utils import timezone
from docx import Document
import requests

from apps.ai_results.models import Alert

from .models import MonitorReport

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def report_period(report_date: date, end_at_now: bool = False):
    tz = timezone.get_current_timezone()
    start = datetime.combine(report_date - timedelta(days=1), time(12, 0))
    end = datetime.combine(report_date, time(12, 0))
    period_start = timezone.make_aware(start, tz)
    period_end = timezone.now() if end_at_now else timezone.make_aware(end, tz)
    return period_start, period_end


def default_report_date():
    return timezone.localdate()


def generate_monitor_report(report_date: date | None = None, end_at_now: bool = False) -> MonitorReport:
    target_date = report_date or default_report_date()
    period_start, period_end = report_period(target_date, end_at_now=end_at_now)
    report, _ = MonitorReport.objects.update_or_create(
        report_date=target_date,
        defaults={
            "period_start": period_start,
            "period_end": period_end,
            "status": MonitorReport.Status.GENERATING,
            "error_message": "",
        },
    )

    alerts = list(
        Alert.objects.select_related("camera")
        .filter(occurred_at__gte=period_start, occurred_at__lt=period_end)
        .order_by("occurred_at", "id")
    )

    try:
        content = _generate_report_content(target_date, period_start, period_end, alerts)
        summary = _extract_summary(content, alerts)
        document_path = _write_word_document(target_date, content)

        report.alert_count = len(alerts)
        report.high_alert_count = sum(1 for alert in alerts if alert.level == "high")
        report.pending_alert_count = sum(1 for alert in alerts if alert.status == Alert.Status.PENDING)
        report.ai_summary = summary
        report.content = content
        report.document_path = document_path
        report.status = MonitorReport.Status.GENERATED
        report.error_message = ""
        report.generated_at = timezone.now()
        report.save()
    except Exception as exc:
        report.status = MonitorReport.Status.FAILED
        report.error_message = str(exc)
        report.generated_at = timezone.now()
        report.save(update_fields=["status", "error_message", "generated_at", "updated_at"])

    return report


def _generate_report_content(report_date, period_start, period_end, alerts):
    prompt = _build_prompt(report_date, period_start, period_end, alerts)
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return _fallback_report(report_date, period_start, period_end, alerts, "未配置 DEEPSEEK_API_KEY，当前使用规则生成日报。")

    response = requests.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是工厂安全监控日报助手。请基于告警事件生成简洁、客观、可执行的中文监控日报。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        return _fallback_report(report_date, period_start, period_end, alerts, "AI 返回内容为空，当前使用规则生成日报。")
    return content


def _build_prompt(report_date, period_start, period_end, alerts):
    lines = [
        f"请生成 {report_date.isoformat()} 的工厂 AI 监控日报。",
        f"统计周期：{timezone.localtime(period_start).strftime('%Y-%m-%d %H:%M')} 至 {timezone.localtime(period_end).strftime('%Y-%m-%d %H:%M')}。",
        "日报必须包含：总体概览、告警等级统计、告警类型统计、重点风险、处理建议。",
        "要求：纯文本，不要 Markdown 表格，不要编造未提供的信息。",
        "",
        "告警事件：",
    ]
    if not alerts:
        lines.append("无告警事件。")
        return "\n".join(lines)

    for alert in alerts:
        occurred = timezone.localtime(alert.occurred_at).strftime("%Y-%m-%d %H:%M:%S")
        camera_name = alert.camera.name if alert.camera else "未关联摄像头"
        lines.append(
            f"- 时间={occurred}; 摄像头={camera_name}; 标题={alert.title}; "
            f"类型={alert.event_type}; 等级={alert.level}; 状态={alert.status}; 说明={alert.description or '无'}"
        )
    return "\n".join(lines)


def _fallback_report(report_date, period_start, period_end, alerts, note=""):
    level_counts = Counter(alert.level for alert in alerts)
    type_counts = Counter(alert.event_type for alert in alerts)
    status_counts = Counter(alert.status for alert in alerts)
    lines = [
        "智安工厂 AI 监控日报",
        "",
        f"日报日期：{report_date.isoformat()}",
        f"统计周期：{timezone.localtime(period_start).strftime('%Y-%m-%d %H:%M')} 至 {timezone.localtime(period_end).strftime('%Y-%m-%d %H:%M')}",
        f"生成说明：{note}" if note else "",
        "",
        "一、总体概览",
        f"本周期共记录 {len(alerts)} 条告警事件。",
        "",
        "二、告警等级统计",
    ]
    lines.extend([f"- {key}: {value}" for key, value in level_counts.items()] or ["- 无"])
    lines.extend(["", "三、告警类型统计"])
    lines.extend([f"- {key}: {value}" for key, value in type_counts.items()] or ["- 无"])
    lines.extend(["", "四、处理状态统计"])
    lines.extend([f"- {key}: {value}" for key, value in status_counts.items()] or ["- 无"])
    lines.extend(["", "五、重点告警"])
    high_alerts = [alert for alert in alerts if alert.level == "high"]
    for index, alert in enumerate((high_alerts or alerts)[:10], start=1):
        occurred = timezone.localtime(alert.occurred_at).strftime("%Y-%m-%d %H:%M:%S")
        camera_name = alert.camera.name if alert.camera else "未关联摄像头"
        lines.append(f"{index}. [{alert.level}] {occurred} {camera_name} - {alert.title}：{alert.description or '无说明'}")
    if not alerts:
        lines.append("本周期无告警事件。")
    lines.extend(["", "六、处理建议", "请优先复核高危和待处理告警，必要时安排现场确认并关闭已处理事件。"])
    return "\n".join(line for line in lines if line != "")


def _extract_summary(content, alerts):
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("智安工厂"):
            return stripped[:500]
    return f"本周期共记录 {len(alerts)} 条告警事件。"


def _write_word_document(report_date, content):
    reports_dir = Path(settings.MEDIA_ROOT) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"monitor-report-{report_date.isoformat()}.docx"
    path = reports_dir / filename

    document = Document()
    document.add_heading("智安工厂 AI 监控日报", level=1)
    for block in content.splitlines():
        text = block.strip()
        if not text:
            continue
        if text.startswith(("一、", "二、", "三、", "四、", "五、", "六、")):
            document.add_heading(text, level=2)
        else:
            document.add_paragraph(text)
    document.save(path)
    return f"reports/{filename}"
