from django.urls import path

from .views import employee_delete_view, employee_face_list_view, employee_list_view, employee_root_view, employee_update_view

urlpatterns = [
    path("", employee_root_view, name="employees-root"),
    path("list/", employee_list_view, name="employee-list"),
    path("<int:employee_id>/", employee_update_view, name="employee-update"),
    path("<int:employee_id>/delete/", employee_delete_view, name="employee-delete"),
    path("<int:employee_id>/faces/", employee_face_list_view, name="employee-face-list"),
]
