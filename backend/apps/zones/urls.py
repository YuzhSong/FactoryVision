from django.urls import path

from .views import placeholder_view, zone_create_view, zone_detail_view, zone_list_view

urlpatterns = [
    path("placeholder/", placeholder_view, name="zones-placeholder"),
    path("", zone_create_view, name="zone-create"),
    path("list/", zone_list_view, name="zone-list"),
    path("<int:zone_id>/", zone_detail_view, name="zone-detail"),
]
