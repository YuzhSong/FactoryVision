import os
import sys

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.utils import timezone

from .services import generate_monitor_report

_scheduler = None


def start_report_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    if os.getenv("MONITOR_REPORT_SCHEDULER_ENABLED", "True").lower() != "true":
        return

    _scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    _scheduler.add_job(
        generate_monitor_report,
        trigger="cron",
        hour=12,
        minute=0,
        id="daily-monitor-report",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()


def scheduler_should_start():
    if os.getenv("RUN_MAIN") == "true":
        return True
    command = " ".join(sys.argv).lower()
    if "daphne" in command:
        return True
    return os.getenv("DJANGO_RUN_MAINLESS_SCHEDULER", "False").lower() == "true"
