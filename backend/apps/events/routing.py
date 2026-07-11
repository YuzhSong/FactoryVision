from django.urls import re_path

from .consumers import RealtimeEventConsumer

websocket_urlpatterns = [
    re_path(r"ws/realtime/(?P<camera_id>\d+)/$", RealtimeEventConsumer.as_asgi()),
]
