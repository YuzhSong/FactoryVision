from django.urls import path

from .views import camera_list_view, placeholder_view

urlpatterns = [
    path("", placeholder_view, name="cameras-placeholder"),
    path("list/", camera_list_view, name="camera-list"),
]
