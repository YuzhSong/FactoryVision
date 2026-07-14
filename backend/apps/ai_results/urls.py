from django.urls import path

from .views import placeholder_view, report_ai_results

urlpatterns = [
    path("", placeholder_view, name="ai-results-placeholder"),
    path("report/", report_ai_results, name="ai-results-report"),
]
