# Change: Camera full CRUD implementation

## Why

摄像头模块之前只有占位接口和列表查询，无法在前端新增、编辑和管理摄像头。AI Service 依赖摄像头列表获取流地址，需要完整的 CRUD 支持。

## What Changes

- 摄像头列表增加 keyword 搜索（名称/编码/位置）、status 筛选和分页
- 新增 POST /api/cameras/ 创建摄像头，code 可选自动生成
- 新增 PUT /api/cameras/{id}/ 编辑摄像头
- 新增 POST /api/cameras/{id}/toggle/ 切换在线/离线/停用状态
- 列表不传分页参数时返回全量（AI Service 兼容）
- Swagger 注解改为中文
- 更新 camera-management spec 和 API 文档

## Affected Specs

- camera-management
