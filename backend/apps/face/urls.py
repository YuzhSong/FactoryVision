from django.urls import path

from .views import face_delete_view, face_enroll_view

urlpatterns = [
    path("enroll/", face_enroll_view, name="face-enroll"),
    path("<int:face_id>/delete/", face_delete_view, name="face-delete"),
]
