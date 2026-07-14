from django.urls import path

from .views import event_list_view, event_media_upload_view, placeholder_view

urlpatterns = [
    path("", placeholder_view, name="events-placeholder"),
    path("list/", event_list_view, name="events-list"),
    path("<int:event_id>/media/", event_media_upload_view, name="events-media-upload"),
]
