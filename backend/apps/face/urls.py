from django.urls import path

from .views import face_enroll_view

urlpatterns = [
    path("enroll/", face_enroll_view, name="face-enroll"),
]
