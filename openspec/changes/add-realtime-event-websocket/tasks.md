# Tasks

- [ ] 安装 channels + daphne
- [ ] `config/settings.py` 注册 channels、配置 ASGI_APPLICATION、设置 CHANNEL_LAYERS
- [ ] `config/asgi.py` 添加 WebSocket 路由
- [ ] 新建 `apps/events/consumers.py` 实现 RealtimeEventConsumer
- [ ] `AI_RESULTS_REPORT_VIEW` 创建事件后推送给 WebSocket 客户端
- [ ] 更新 event-alert spec
- [ ] 更新 04-api-design.md WebSocket 接口
- [ ] 测试 WebSocket 连接和消息推送
- [ ] 归档 change
