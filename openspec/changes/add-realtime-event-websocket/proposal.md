# Change: Add realtime event WebSocket push

## Why

实时监控面板右侧"实时事件流"目前使用 mock 数据，标记为"WebSocket planned"。AI Service 上报检测结果后，前端无法实时看到新事件，需要手动刷新。需要实现 WebSocket 推送，让监控页面实时展示检测事件。

## What Changes

- 安装 Django Channels + daphne（WebSocket 支持）
- 新建 `WS /ws/realtime/{cameraId}/` WebSocket 端点
- AI 上报检测结果时，后端推送给对应摄像头的 WebSocket 客户端
- 前端 MonitorView 建立 WebSocket 连接，实时接收事件

## Affected Specs

- event-alert
- video-stream（监控页面）
