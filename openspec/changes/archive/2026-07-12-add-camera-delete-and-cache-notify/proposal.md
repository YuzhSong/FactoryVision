# Change: Add camera delete and AI cache notification for all camera mutations

## Why

摄像头创建、编辑、切换状态后 AI Service 缓存是旧的。缺少删除接口。需要补齐通知和删除。

## What Changes

- `DELETE /api/cameras/{id}/delete/` — 删除摄像头，级联删除关联 zone
- 创建/编辑/切换/删除成功后通知 AI Service 刷新摄像头缓存
- Swagger 注解中文

## Affected Specs

- camera-management
