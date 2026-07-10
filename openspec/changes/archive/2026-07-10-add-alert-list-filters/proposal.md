# Change: Add alert list search filters

## Why

当前告警中心列表接口缺少关键词搜索和时间范围筛选，前端告警页面筛选栏（关键词、等级、状态、日期区间）无法完整接入。需要补齐查询参数，并将 Swagger 文档改为中文。

## What Changes

- `GET /api/alerts/list/` 新增 `keyword` 参数（模糊搜索 title）
- `GET /api/alerts/list/` 新增 `startTime` / `endTime` 参数（按 occurred_at 时间范围筛选）
- `POST /api/alerts/{id}/handle/` Swagger 注解改为中文
- `GET /api/alerts/list/` Swagger 注解改为中文
- 更新 event-alert spec

## Affected Specs

- event-alert
