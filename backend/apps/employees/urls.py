from django.urls import path

from .views import employee_list_view, employee_root_view

urlpatterns = [
    path("", employee_root_view, name="employees-root"),
    path("list/", employee_list_view, name="employee-list"),
]
