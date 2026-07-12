# Change: Add employee update and delete endpoints with AI cache notification

## Why

员工模块当前只有创建和列表，缺少编辑和删除。编辑姓名/工号后 AI Service 内存中的人脸库信息过时，删除员工后人脸编码需要从 AI Service 清除。

## What Changes

- `PUT /api/employees/{id}/` — 编辑员工信息（所有字段可选）
- `DELETE /api/employees/{id}/` — 删除员工，级联 delete face_feature 和本地图片
- 编辑成功 → 调 `POST /cache/employees/upsert` 通知 AI Service
- 删除成功 → 调 `POST /cache/employees/delete` 通知 AI Service

## Affected Specs

- employee-management
