# 本地开发数据库

本地 Backend 默认使用 `backend/db.sqlite3`。该文件由 migration 和 seed 重建并被 Git 忽略，不得提交。

## 初始化

从仓库根目录执行：

```powershell
backend\.venv\Scripts\python.exe backend\manage.py migrate
backend\.venv\Scripts\python.exe backend\manage.py seed_dev_data
```

`seed_dev_data` 可重复执行，用于创建本地演示用户、摄像头、员工、区域、正式 Event 和 Alert 数据。具体数量可能随 seed 脚本调整，不应作为业务约束。

## 重置

停止 Backend，确认目标确实是 `backend/db.sqlite3` 后删除该本地文件，再重新执行 `migrate` 和 `seed_dev_data`。不要删除或覆盖生产数据库。

## 边界

- 不使用 `.codex-runlogs/*.sqlite3` 作为日常数据库或 seed 来源。
- `events.Event` 是唯一正式事件模型，`Alert.event` 直接关联它。
- `/api/ai-results/report/` 只创建 Event 以及可选 Alert，不写入旧 AIEvent 兼容模型。
- 生产环境使用 PostgreSQL，不使用本地 SQLite 文件。
