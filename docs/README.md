# Factory Vision 文档中心

本目录保存项目最终交付文档。`01`–`11` 是当前版本的正式基线；操作指南、验证报告和历史材料分别归档，避免开发期结论与最终现状混用。

## 正式文档

| 文档 | 内容 |
| --- | --- |
| [01-project-overview.md](01-project-overview.md) | 项目定位、已交付能力、演示闭环和范围边界 |
| [02-requirements.md](02-requirements.md) | P0/P1/P2 需求与最终实现状态 |
| [03-architecture-design.md](03-architecture-design.md) | 服务关系、数据流、部署边界 |
| [04-api-design.md](04-api-design.md) | Backend、AIService 与 WebSocket 接口约定 |
| [05-database-design.md](05-database-design.md) | 当前数据模型、关系和字段 |
| [06-ai-service-design.md](06-ai-service-design.md) | 检测、调度、视频处理和事件上报 |
| [07-frontend-design.md](07-frontend-design.md) | 页面、路由、播放器和实时消息 |
| [08-development-guide.md](08-development-guide.md) | 开发、提交、接口和 OpenSpec 规范 |
| [09-team-division.md](09-team-division.md) | 团队职责与协作方式 |
| [10-deployment-cicd.md](10-deployment-cicd.md) | 本地环境、生产部署和 Jenkins 流程 |
| [11-test-plan.md](11-test-plan.md) | 自动化测试与最终演示验收 |

## 目录结构

```text
docs/
├─ 01-11                         正式交付文档
├─ api/                          导出的 OpenAPI JSON/YAML
├─ guides/                       可执行操作指南
├─ reports/                      阶段验证与迁移报告
├─ archive/                      已过期的分析或历史接口材料
├─ daily/                        团队日报模板
└─ images/                       文档图片
```

### 操作指南

- [生产部署与回滚](guides/production-deployment.md)
- [本地数据库初始化](guides/local-dev-database.md)
- [OpenSpec 使用说明](guides/openspec.md)
- [Swagger 使用说明](guides/swagger.md)
- [OpenAPI 导出说明](api/README.md)

### 验证报告

- [AIService 本地链路测试报告](reports/aiservice-local-chain-test-report.md)
- [Event 模型迁移报告](reports/event-model-migration-report.md)

`archive/` 中的内容仅用于追溯，不代表当前系统能力；最新接口以 Swagger、`api/` 导出文件和 `04-api-design.md` 为准。

## 维护规则

1. 功能现状改变时同步更新对应编号文档和 `openspec/specs/`。
2. 新需求在 `openspec/changes/` 建立变更，完成后归档到 `openspec/changes/archive/`。
3. 运行日志、模型权重、数据库、截图、关键帧和回放视频不纳入正式文档目录。
4. 历史报告不改写结论；失效材料移动到 `archive/` 并在索引中明确其性质。
5. Frontend 只访问 Backend API 与视频播放地址；AIService 不直接写数据库。
