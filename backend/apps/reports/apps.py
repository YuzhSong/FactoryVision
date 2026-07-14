from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"

    def ready(self):
        from .scheduler import scheduler_should_start, start_report_scheduler

        if scheduler_should_start():
            start_report_scheduler()
