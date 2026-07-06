from django.urls import path

from .views import placeholder_view

urlpatterns = [
    path("", placeholder_view, name="cameras-placeholder"),
]
