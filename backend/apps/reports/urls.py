from django.urls import path

from .views import report_detail_view, report_download_view, report_generate_view, report_list_view

urlpatterns = [
    path("list/", report_list_view, name="reports-list"),
    path("generate/", report_generate_view, name="reports-generate"),
    path("<str:report_id>/", report_detail_view, name="reports-detail"),
    path("<str:report_id>/download/", report_download_view, name="reports-download"),
]
