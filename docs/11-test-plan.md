# 测试与验收

## 测试目标

验证“配置—推流—检测—播放—事件—告警—证据—日报”的完整闭环，并确保输入断流、慢模型和媒体失败不会导致无界积压或页面崩溃。

## 自动化验证

| 范围 | 命令 | 重点 |
| --- | --- | --- |
| Python 环境 | `powershell -File scripts/check-python-env.ps1` | AIService 必须为仓库 Python 3.11 |
| Backend | `powershell -File scripts/test-backend.ps1` | API、模型、WebSocket、事件、报告 |
| AIService | `powershell -File scripts/test-ai-service.ps1` | 检测、缓存、流处理、事件策略 |
| Frontend | `npm.cmd --prefix frontend run build` | Vue 编译和生产构建 |
| OpenSpec | `npx.cmd openspec validate --all` | 主规格和活动变更格式 |

## 核心验收用例

| 编号 | 场景 | 预期结果 |
| --- | --- | --- |
| E2E-01 | 登录并访问管理页面 | JWT 生效，未登录访问被重定向 |
| E2E-02 | 新增员工并录入人脸 | 人脸图片和 512 维特征保存，人脸库刷新 |
| E2E-03 | 新增摄像头和区域 | 摄像头可选择，区域可绘制、保存和预览 |
| E2E-04 | 首次进入监控页 | 人物框强制开启，四项开关首次仅区域开启 |
| E2E-05 | 修改开关后重新进入 | 恢复上次开关状态，启动参数与页面一致 |
| E2E-06 | 单人全检测 | 带框流持续播放，帧龄不持续增长 |
| E2E-07 | 多人只开人脸 | 身份标签可见，性能优于全部检测同时开启 |
| E2E-08 | 只开安全帽 | 人物框绿色；Helmet/No Helmet 头部框持续稳定 |
| E2E-09 | 摔倒或区域风险 | Event/Alert 入库并通过 WebSocket 到达前端 |
| E2E-10 | 打开告警详情 | 关键帧、视频或明确空状态可见，原始证据可追溯 |
| E2E-11 | 处置告警 | 状态按 pending → processing → closed 流转 |
| E2E-12 | 生成 AI 日报 | 页面预览中文正常，关键帧可见，下载文件为有效 DOCX |
| E2E-13 | 关闭手机推流 | AIService 停止旧帧处理并显示明确错误，不继续输出旧画面 |
| E2E-14 | 恢复推流并重新启动 | 新流可恢复，状态和播放器重新正常 |

## 性能与延迟观察

使用 `/streams/status` 同时记录：

- `processFps` 与最新帧年龄；
- 各检测最近耗时、平均耗时和 p95；
- 推理、绘制、事件/录像、writer 入队与 FFmpeg 写入耗时；
- 输入重连、陈旧帧丢弃和输出 writer 丢帧；
- 当前检测开关。

多人场景的人脸识别耗时通常随人脸数量增加。演示时应按目标选择检测项，不用输出固定 FPS 的“看起来流畅”替代真实帧龄指标。

## 发布前检查

1. Git 工作区只包含预期改动，不提交数据库、日志、模型和媒体文件。
2. OpenSpec 活动目录只保留未完成变更，已完成项均归档。
3. Backend migration 已应用，生产环境变量完整。
4. Frontend 构建成功，下载接口返回真实 DOCX。
5. AIService 使用仓库 Python 3.11，模型与 FFmpeg 可用。
6. 云端 Backend/Frontend、SRS 和本地 AIService 的网络路径全部可达。
