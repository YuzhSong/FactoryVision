# Event Model Migration Report

## 测试时间

- 时间：2026-07-09 16:27:35 +08:00
- 分支：`rainy`
- 当前 HEAD：`1a074b3f Merge PR #10 into dev`

## Git 状态

- 已切换到 `rainy`。
- 本地 `rainy` 当前已经合入本地可用的 `origin/dev` 引用：`1a074b3f`。
- 本轮前置 `git fetch origin` 曾失败，错误为 GitHub 网络连接超时/连接重置。因此本次合并基于本机已有的 `origin/dev` 最新引用。
- 合并未出现冲突。
- 本轮未提交 commit，未 push。

## OpenSpec

- 变更名称：`consolidate-ai-events-into-events`
- 路径：`openspec/changes/consolidate-ai-events-into-events/`
- 已新增：
  - `proposal.md`
  - `design.md`
  - `tasks.md`
  - `specs/ai-results/spec.md`
  - `specs/event-alert/spec.md`
- 校验结果：
  - `openspec validate consolidate-ai-events-into-events`：通过
  - `openspec validate --all --no-interactive`：15 passed, 0 failed

## 为什么迁移

> Historical note: this report describes the completed compatibility transition. The later `remove-ai-event-compatibility` change ends that period: `AIEvent` is removed, `Event` is the only formal event model, and `Alert.event` directly references it.

`AIEvent` was a temporary persistence target used to establish the AIService reporting chain. It stored camera, event type, occurrence time, bbox, confidence, snapshot, and raw payload.

项目中已有 `events` app，但此前仍是占位模块。为了避免后续告警中心、事件审计、回放、检索都继续依赖 `ai_results` 下的临时模型，本轮将正式事件记录收敛到 `events.Event`，同时保留 `AIEvent` 作为兼容过渡。

## 新 Event 模型

新增模型：`backend/apps/events/models.py` 中的 `Event`。

字段：

- `camera`
- `camera_identifier`
- `event_type`
- `source`
- `severity`
- `status`
- `occurred_at`
- `frame_id`
- `track_id`
- `bbox`
- `confidence`
- `snapshot_path`
- `payload`
- `created_at`
- `updated_at`

数据库表名：`event`。

## AIEvent 处理方式

本轮没有删除 `AIEvent`，也没有删除 `apps.ai_results`。

当前策略是兼容期双写：

- 每条 AIService 上报结果先写入正式 `events.Event`。
- 同时继续写入一条 `AIEvent`，防止已有测试、迁移、后台或潜在代码依赖被打断。
- 响应中的 `eventIds` 现在表示正式 `events.Event.id`。
- 响应中额外返回 `aiEventIds`，用于过渡期排查。

## `/api/ai-results/report/` 行为

接口地址和 AIService payload 未改变。

当前行为：

- 校验现有 payload。
- 根据 `cameraId` 查找 `Camera`。
- 对每条有 `type` 的 result：
  - 创建一条 `events.Event`
  - 创建一条兼容 `AIEvent`
  - 如果是告警类类型，再创建 `Alert`
- 返回：
  - `eventIds`
  - `aiEventIds`
  - `alertIds`
  - `acceptedResults`
  - `rejectedResults`
  - `cameraId`
  - `frameId`

## Alert 派生关系

当前 `Alert.event` 原本指向 `AIEvent`。为了低风险迁移，本轮未重命名该字段。

新增字段：

- `Alert.system_event`：指向正式 `events.Event`

因此当前告警会同时保留：

- 旧兼容链路：`Alert.event -> AIEvent`
- 新正式链路：`Alert.system_event -> Event`

后续如果确认无旧代码依赖，可单独设计一次字段收敛和历史数据迁移。

## 迁移命令

使用本地测试库：

```powershell
$env:DB_NAME='D:\Code\FactoryVision\.codex-runlogs\backend-chain-test.sqlite3'
python manage.py makemigrations events ai_results
python manage.py migrate
```

迁移结果：

- `backend/apps/events/migrations/0001_initial.py`
- `backend/apps/ai_results/migrations/0002_alert_system_event.py`

## 测试结果

已运行：

```powershell
$env:DB_NAME='D:\Code\FactoryVision\.codex-runlogs\backend-chain-test.sqlite3'
python manage.py test apps.ai_results apps.events
```

结果：

- 4 tests passed
- System check identified no issues

代表性接口验证：

- `PERSON_DETECTION`：HTTP 200，新增 1 条 `Event`，新增 1 条兼容 `AIEvent`，未新增 `Alert`
- `ZONE_WARNING`：HTTP 200，新增 1 条 `Event`，新增 1 条兼容 `AIEvent`，新增 1 条 `Alert`
- `Alert.system_event_id` 已指向正式 `Event`

后端入口验证：

- `GET /api/health/`：200
- `GET /api/cameras/list/`：200
- `GET /api/ai-results/`：200

额外验证：

- `python manage.py check`：通过，System check identified no issues
- `npm run build`：通过
- 前端 build 存在 Rolldown 对 `@vueuse/core` pure annotation 的警告，以及 chunk size warning；构建成功，非本轮事件迁移阻断项。

## 风险和待确认点

- 当前为兼容期双写，`Event` 和 `AIEvent` 会同时增长，后续需要决定何时停止写 `AIEvent`。
- `Alert.event` 字段名仍指向 `AIEvent`，正式 Event 关系暂时通过 `system_event` 承接；这是低风险方案，但字段命名不是最终最干净形态。
- 本轮未改前端告警中心列表，也未新增事件查询 API。
- 本轮未启动真实 AIService 视频链路，只验证后端事件迁移和接口兼容。
- 因 GitHub 网络问题，本轮未成功重新 fetch 远端，只使用了本地已有 `origin/dev=1a074b3f`。

## 修改文件

- `backend/apps/events/models.py`
- `backend/apps/events/admin.py`
- `backend/apps/events/migrations/0001_initial.py`
- `backend/apps/ai_results/models.py`
- `backend/apps/ai_results/views.py`
- `backend/apps/ai_results/tests.py`
- `backend/apps/ai_results/migrations/0002_alert_system_event.py`
- `openspec/changes/consolidate-ai-events-into-events/`
- `docs/reports/event-model-migration-report.md`

## 下一步建议

1. 先让前后端在 dev 环境确认 `eventIds` 改为正式 `Event.id` 后没有调用方误用。
2. 后续新增事件中心查询接口时，直接基于 `events.Event` 做列表、筛选、详情。
3. 确认无旧依赖后，再做一次单独 OpenSpec 变更，将 `AIEvent` 从双写改为停止写入或数据归档。
4. 再进一步把 `Alert.event` 字段清理为正式指向 `Event`，并迁移历史数据。
