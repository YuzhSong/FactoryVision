from django.urls import path

from .views import face_delete_view, face_enroll_view, face_library_view

urlpatterns = [
    path("enroll/", face_enroll_view, name="face-enroll"),
    path("library/", face_library_view, name="face-library"),
    path("<int:face_id>/delete/", face_delete_view, name="face-delete"),
]
