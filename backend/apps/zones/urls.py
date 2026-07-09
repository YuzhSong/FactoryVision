from django.urls import path

from .views import placeholder_view, zone_list_view

urlpatterns = [
    path("", placeholder_view, name="zones-placeholder"),
    path("list/", zone_list_view, name="zone-list"),
]
