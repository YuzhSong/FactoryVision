# 开发指南

## 开发原则

1. 先对齐文档和 OpenSpec，再实现功能。
2. 每次改动控制在单一目标范围内。
3. 未实现能力标记为 `planned`，不得在文档或提交说明中声称已完成。
4. 接口、数据库、页面和 AI 输出格式变更时必须同步更新文档。

## Git 分支规范

| 分支 | 用途 |
| --- | --- |
| `main` | 稳定版本，只保留可交付代码 |
| `dev` | 开发集成分支，团队功能合并目标 |
| `feature/xxx` | 功能开发分支 |
| `fix/xxx` | 问题修复分支 |
| `docs/xxx` | 文档修改分支 |

禁止直接提交 `main`。所有功能和文档修改应通过分支、PR、Review 后合并到 `dev`。

## Commit 规范

| 前缀 | 说明 | 示例 |
| --- | --- | --- |
| `feat:` | 新功能 | `feat: add camera list api` |
| `fix:` | 问题修复 | `fix: handle empty stream url` |
| `docs:` | 文档修改 | `docs: add api design` |
| `refactor:` | 重构 | `refactor: split alert service` |
| `test:` | 测试 | `test: add camera api tests` |
| `chore:` | 工程杂项 | `chore: update gitignore` |

## PR 规范

PR 描述应包含：

1. 改动范围。
2. 关联 Issue 或 OpenSpec 条目。
3. 测试方式和结果。
4. 是否涉及接口、数据库、AI 输出格式或部署方式变更。
5. 是否更新文档。

Review 要点：

1. 是否越权修改其他成员负责范围。
2. 是否破坏已有启动流程。
3. 是否符合接口和分层边界。
4. 是否有必要测试。
5. 是否存在未说明的业务逻辑扩张。

## 接口规范

1. REST API 使用 JSON 请求和响应。
2. 响应格式统一为 `code`、`message`、`data`、`requestId`。
3. 列表接口统一支持 `page`、`pageSize`。
4. 新增或变更接口必须更新 `04-api-design.md`。
5. 后端负责参数校验、权限校验和数据一致性。
6. 前端不得绕过后端直接访问数据库。

## 前端代码规范

1. 页面放在 `frontend/src/views/`。
2. 通用布局放在 `frontend/src/layouts/`。
3. 通用 API 调用通过 `frontend/src/api/http.js` 封装。
4. 页面组件应优先消费后端 API，不写散落的大量 mock 数据。
5. 实时消息统一通过 WebSocket 消费，离开页面时关闭连接。
6. 新增页面必须更新 `07-frontend-design.md`。

## 后端代码规范

1. Django app 按业务边界划分，如 users、employees、cameras、zones、events、attendance、ai_results。
2. API 视图统一返回 `common.response.api_response` 或后续统一响应封装。
3. 模型变更必须生成 migration，并更新 `05-database-design.md`。
4. 业务校验放在后端，不依赖前端校验保证安全。
5. 新增接口必须接入 Swagger / OpenAPI。

## AI 服务代码规范

1. AI 服务只负责读取视频、执行检测、生成结果和上报。
2. AI 服务不得直接写数据库。
3. 检测结果必须使用结构化 JSON。
4. 模型加载、阈值、后端地址等配置应通过配置文件或环境变量管理。
5. 新增检测类型必须更新 `06-ai-service-design.md` 和 `04-api-design.md`。

## OpenSpec 使用规范

1. 新功能开发前先补充或更新 `openspec/specs/` 中对应规范。
2. 需求范围变化必须通过 OpenSpec 记录。
3. PR 中说明关联的 OpenSpec 文件。
4. OpenSpec 与 `docs/` 冲突时，应同步修正文档并在 PR 中说明。

## Codex 使用规范

1. 使用 Codex 前先明确本次任务范围。
2. 文档任务只修改文档目录和必要导航，不生成业务代码。
3. 功能任务只修改所属模块，不一次性生成大范围业务。
4. 让 Codex 修改接口、数据库或 AI 输出格式时，必须要求同步更新文档。
5. Codex 生成内容需要人工 Review 后合并。

## 明确禁止

1. 不得直接提交 `main`。
2. 不得前端直连数据库。
3. 不得 AI 服务直接写数据库。
4. 不得一次性生成大范围业务。
5. 不得删除已有功能。
6. 不得修改接口但不更新文档。
7. 不得在未实现时将 planned 功能描述为 implemented。
8. 不得随意修改其他成员负责范围的代码或文档。
