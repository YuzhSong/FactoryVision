from django.db import models


class MonitorReport(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATING = "generating", "Generating"
        GENERATED = "generated", "Generated"
        FAILED = "failed", "Failed"

    report_date = models.DateField(unique=True, verbose_name="日报日期")
    period_start = models.DateTimeField(verbose_name="统计开始时间")
    period_end = models.DateTimeField(verbose_name="统计结束时间")
    alert_count = models.PositiveIntegerField(default=0, verbose_name="告警总数")
    high_alert_count = models.PositiveIntegerField(default=0, verbose_name="高危告警数")
    pending_alert_count = models.PositiveIntegerField(default=0, verbose_name="待处理告警数")
    ai_summary = models.TextField(blank=True, default="", verbose_name="AI 摘要")
    content = models.TextField(blank=True, default="", verbose_name="日报正文")
    document_path = models.CharField(max_length=512, blank=True, default="", verbose_name="文档相对路径")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True, default="", verbose_name="生成错误")
    generated_at = models.DateTimeField(null=True, blank=True, verbose_name="生成时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "monitor_report"
        ordering = ["-report_date"]
