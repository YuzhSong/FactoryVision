# Change: Zone create API

## Why

警戒区域模块之前只有列表查询接口，前端可以选择摄像头查看已有区域，但无法创建新区域。需要补齐创建接口。

## What Changes

- 新增 ZoneCreateSerializer 和 zone_create_view
- 列表序列化器删冗余 polygon 字段
- Swagger 注解改为中文
- 更新 warning-zone spec 和 API 文档

## Affected Specs

- warning-zone
