import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class RealtimeEventConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time detection events per camera."""

    async def connect(self):
        self.camera_id = self.scope["url_route"]["kwargs"]["camera_id"]
        self.group_name = f"realtime_{self.camera_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # 前端发来的消息暂不处理，预留
        pass

    async def event_message(self, event):
        """Handle event_message type - push to WebSocket client."""
        await self.send_json(event["data"])

    @classmethod
    async def push_event(cls, channel_layer, camera_id: int, data: dict):
        """Push event to all clients in a camera's group."""
        await channel_layer.group_send(
            f"realtime_{camera_id}",
            {
                "type": "event.message",
                "data": data,
            },
        )
