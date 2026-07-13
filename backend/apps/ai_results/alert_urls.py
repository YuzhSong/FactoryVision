from django.urls import path

from .views import alert_detail_view, alert_handle_view, alert_list_view

urlpatterns = [
    path("list/", alert_list_view, name="alerts-list"),
    path("<int:alert_id>/detail/", alert_detail_view, name="alerts-detail"),
    path("<int:alert_id>/handle/", alert_handle_view, name="alerts-handle"),
]
