from django.urls import path

from .views import event_list_view, placeholder_view

urlpatterns = [
    path("", placeholder_view, name="events-placeholder"),
    path("list/", event_list_view, name="events-list"),
]
