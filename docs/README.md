# Docs README

本文档目录用于维护“智安工厂实时视频分析监测系统”的项目说明、需求、架构、接口、数据库、AI 服务、前端、开发规范、团队协作、部署和测试资料。

## 文档清单

| 文档 | 用途 |
| --- | --- |
| `01-project-overview.md` | 项目背景、目标、定位、核心场景和演示闭环 |
| `02-requirements.md` | 按 P0/P1/P2 梳理功能需求、输入输出和验收标准 |
| `03-architecture-design.md` | 总体架构、服务关系、数据流和边界约束 |
| `04-api-design.md` | REST API、WebSocket、统一响应格式和错误码规范 |
| `05-database-design.md` | 数据库实体、字段、关系和 ER 图 |
| `06-ai-service-design.md` | AI 服务职责、模块结构、检测输出格式和算法约束 |
| `07-frontend-design.md` | 前端页面、路由、组件划分和实时消息消费方式 |
| `08-development-guide.md` | Git、Commit、PR、接口、前后端、AI、OpenSpec 和 Codex 使用规范 |
| `09-team-division.md` | 六人成员分工、交付物、对接对象和协作流程 |
| `10-deployment-cicd.md` | 本地启动、数据库初始化、视频流服务、Jenkins 阶段和排查 |
| `11-test-plan.md` | 功能、接口、视频流、AI 上报、告警、权限和 Jenkins 测试计划 |
| `daily/README.md` | 工作日报模板和填写规则 |
| `images/README.md` | 图片目录用途和命名规则 |

## 历史文档处理

早期的 `prd.md`、`architecture.md`、`api.md`、`database.md`、`deployment.md` 内容已合并到编号文档体系中，并已清理。后续以当前编号文档为准。

早期的 `test-report.md` 也已由 `11-test-plan.md` 覆盖并清理。

## 文档维护规则

1. 所有正式文档使用 Markdown。
2. 标题层级从 `#` 开始按顺序组织，不使用临时标题或占位词。
3. 文档描述必须与当前代码状态一致，未实现能力统一标记为 `planned`。
4. 修改接口、数据库、页面、AI 输出格式或部署方式时，必须同步更新对应文档。
5. 新增文档时必须更新本文件的文档清单。
6. 文档中涉及业务边界时，应明确前端只访问后端 API，AI 服务只通过后端 API 上报。
7. 每个成员优先维护自己负责范围的文档，跨模块修改需要在 PR 中说明原因。
