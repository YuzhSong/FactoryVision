from django.urls import path

from .views import camera_create_view, camera_list_view, camera_toggle_view, camera_update_view, placeholder_view

urlpatterns = [
    path("placeholder/", placeholder_view, name="cameras-placeholder"),
    path("", camera_create_view, name="camera-create"),
    path("list/", camera_list_view, name="camera-list"),
    path("<int:camera_id>/", camera_update_view, name="camera-update"),
    path("<int:camera_id>/toggle/", camera_toggle_view, name="camera-toggle"),
]
