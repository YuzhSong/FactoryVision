# Spec vs Implementation 对账审计报告

**审计日期：** 2026-07-08  
**审计范围：** `openspec/specs/` 下全部 9 份 spec + `openspec/project.md`  
**审计方法：** 只读代码比对，逐份 spec 与 backend/ / frontend/ / ai-service/ 实际代码对照  
**输出目录：** `openspec/audit/`

---

## 一、总表：每份 spec 的判定结果

| Spec 文件 | 判定 | 关键证据文件 | 简要说明 |
|-----------|------|-------------|---------|
| `abnormal-behavior.md` | ⚠️ 不一致 | `ai-service/modules/person_detector.py`, `stream_reader.py`, `fall_detector.py`, `running_detector.py`, `zone_detector.py` | Constraints 称 "YOLO model loading / real video frame reading / production inference remain planned"，但 YOLO 加载代码、RTMP 帧读取管线、fall/running/zone 三种检测器均已完整实现。仅 helmet detector 和模型权重文件真正为 planned。 |
| `attendance.md` | ✅ 一致 | `backend/apps/attendance/`, `frontend/src/views/AttendanceView.vue` | Spec 为占位描述，代码也是纯占位（空 models、stub view、静态前端壳）。 |
| `employee-management.md` | ⚠️ 不一致 | `backend/apps/employees/models.py`, `views.py`, `tests.py`; `frontend/src/views/EmployeesView.vue` | Spec 仅描述 "placeholder page / placeholder endpoint"，但后端已实现完整 CRUD（Employee 模型 + 迁移 + 创建/列表 API + 5 个测试）。前端仍为静态占位页。 |
| `event-alert.md` | ✅ 一致 | `backend/apps/events/`, `frontend/src/views/AlertsView.vue` | Spec 为占位描述，代码也是纯占位（空 models、stub view、静态前端壳）。 |
| `face-recognition.md` | ⚠️ 不一致 | `ai-service/modules/face_recognition_service.py` (616行); `ai-service/tests/test_face_recognition_service.py` | Spec 称 "placeholder classes and methods for future model integration"，但代码已实现完整的 InsightFace 模型加载、特征提取、余弦相似度匹配（阈值 0.45）、人脸-人体关联分配。后端和前端人脸 API 仍为 stub。 |
| `jenkins-cicd.md` | ⚠️ 不一致 | `Jenkinsfile` (257行) | Spec 要求 "four stages SHALL be present with syntax-valid placeholders"，实际 8 个 stage，其中 6 个执行真实命令，2 个为占位。spec 的核心要求（4 个 stage、均为 placeholder）均被违反。 |
| `person-detection.md` | ✅ 一致 | `ai-service/modules/person_detector.py`, `frame_annotator.py` | Spec 要求输出 bbox/trackId/confidence 并绘制到视频流，代码完整实现 YOLO + IoU tracker + OpenCV 标注。 |
| `video-stream.md` | ✅ 一致 | `frontend/src/views/MonitorView.vue`, `ai-service/modules/stream_reader.py`, `stream_writer.py`, `processed_stream_service.py` | Spec 要求 WebRTC 播放 + RTMP 接入。均已实现：MonitorView WebRTC/HTTP-FLV 双链路播放，StreamReader RTMP 拉流，FFmpegStreamWriter RTMP 推流。但 spec 未提及双链路切换、/streams/start|stop|status 端点等细节。 |
| `warning-zone.md` | ✅ 一致 | `backend/apps/zones/`, `frontend/src/views/ZonesView.vue` | Spec 为占位描述，代码也是纯占位（空 models、stub view、静态前端壳）。 |
| `project.md` | ⚠️ 不一致 | 综合 | Scope 声称 "当前阶段：项目骨架搭建" 和 "暂不实现复杂业务逻辑和真实模型推理"，但 Employee CRUD、Face Recognition (InsightFace)、Person Detection (YOLO)、RTMP 流处理管线均已超出骨架阶段。 |

### 判定统计

```
✅ 一致:   5 份 (attendance, event-alert, person-detection, video-stream, warning-zone)
⚠️ 不一致: 5 份 (abnormal-behavior, employee-management, face-recognition, jenkins-cicd, project.md)
❌ 未实现: 0 份
```

---

## 二、内部矛盾清单

### 2.1 abnormal-behavior.md — Constraints 过时

**原文：**
> "YOLO model loading, real video frame reading and production inference remain planned until model files and runtime environment are confirmed."

**实际代码状态：**

| 声称 "planned" 的能力 | 实际代码状态 | 证据 |
|----------------------|------------|------|
| YOLO model loading | ✅ 已实现 | `person_detector.py` L53-62: `from ultralytics import YOLO` + `YOLO(model_path)` |
| Real video frame reading | ✅ 已实现 | `stream_reader.py`: `cv2.VideoCapture` + reconnect + frame sampling |
| Production inference | ✅ 已实现（代码层面） | `person_detector.py` L65-117: `model.predict(source=frame, ...)` 真实推理调用 |
| Fall detection | ✅ 已实现（纯算法） | `fall_detector.py`: bbox 宽高比阈值判定 |
| Running detection | ✅ 已实现（纯算法） | `running_detector.py`: 像素速度计算 |
| Zone warning | ✅ 已实现（纯算法） | `zone_detector.py`: 射线法 + 边缘距离 |

**唯一真正为 "planned" 的：**
- 模型权重文件（`*.pt`、`*.onnx`）不存在于仓库中
- 安全帽检测模型（`helmet_detector.py` 返回空列表，无真实模型）

---

### 2.2 project.md — Scope 声明过时

**原文：**
> "当前阶段：项目骨架搭建" / "暂不实现复杂业务逻辑和真实模型推理"

**已超出骨架的实现：**
- Employee CRUD（模型 + 迁移 + 创建/列表 API + 5 个测试）
- 用户认证（JWT + 登录/登出/me 端点 + 5 个测试 + 前端路由守卫）
- 人脸识别（InsightFace 616 行完整服务）
- 人员检测（YOLO 推理 + IoU 追踪器）
- RTMP 流处理管线（双线程采集/处理 + FFmpeg 推流 + 帧丢弃优化）
- 前端多链路播放（WebRTC + HTTP-FLV）

---

### 2.3 docs/10-deployment-cicd.md — 文档过时（跨文件矛盾）

该文档称归档阶段为 `planned`，但 Jenkinsfile Stage 6 (Archive Artifacts) 已实现。另外 Mermaid 图仅显示 5 个 stage，实际有 8 个。

---

## 三、缺失 Spec 清单及建议

| # | 缺失 Spec | 代码模块 | 实现程度 | 建议文件名 |
|---|----------|---------|---------|-----------|
| 1 | **用户认证** | `backend/apps/users/` + `frontend/src/views/LoginView.vue` + router guard | 完整实现（模型、JWT、5 测试） | `authentication.md` |
| 2 | **摄像头管理** | `backend/apps/cameras/`（占位） + `frontend/src/views/CamerasView.vue`（静态 UI） | 后端占位/前端有 UI | `camera-management.md` |
| 3 | **AI 结果上报** | `backend/apps/ai_results/` + `ai-service/modules/backend_client.py` | 实现存根（校验+接收，不持久化） | `ai-results.md` |
| 4 | **生产安全配置** | `backend/config/settings.py` + `Jenkinsfile` Stages 7-8 | 仅有开发默认值 | `production-config.md` |
| 5 | **统一 API 响应格式** | `backend/common/response.py` | 完整实现（全部 app 使用） | `api-conventions.md` |
| 6 | **仪表盘** | `frontend/src/views/DashboardView.vue` | 前端静态占位 | `dashboard.md`（P3 低优先级） |

---

## 四、优先级建议

按"业务风险 × 使用频率"排序：

| 优先级 | Spec | 行动 | 理由 |
|--------|------|------|------|
| 🔴 P0 | `jenkins-cicd.md` | 重写 | CI 是每天使用的基础设施，spec 与实际 8-stage pipeline 完全脱节 |
| 🔴 P0 | `project.md` | 更新 Scope | 项目阶段描述误导新成员：大量模块已超出骨架阶段 |
| 🔴 P0 | **新增 `authentication.md`** | 新建 | 认证是安全边界，无 spec 意味着无明确的安全契约 |
| 🔴 P0 | **新增 `api-conventions.md`** | 新建 | 统一响应格式是前后端契约，全部 API 依赖它 |
| 🟠 P1 | `abnormal-behavior.md` | 更新 Constraints | 声称 "planned" 的能力多数已实现，误导开发判断 |
| 🟠 P1 | `employee-management.md` | 重写 | 后端 CRUD 已实现但 spec 仍是 placeholder |
| 🟠 P1 | `face-recognition.md` | 重写 | 616 行生产代码被 spec 描述为 "placeholder classes" |
| 🟡 P2 | **新增 `ai-results.md`** | 新建 | AI 上报端点是 AI→后端的核心数据通道 |
| 🟡 P2 | **新增 `camera-management.md`** | 新建 | cameraId 在多份 spec 中被引用但无独立 spec |
| 🟡 P2 | `video-stream.md` | 补充细节 | 双链路切换、/streams/start|stop|status 端点等未写入 spec |
| 🟢 P3 | `person-detection.md` | 补充细节 | 基本一致，可补充 tracker 算法、model fallback 逻辑 |
| 🟢 P3 | **新增 `production-config.md`** | 新建 | 生产部署的硬性安全要求应文档化 |
| 🟢 P3 | **新增 `dashboard.md`** | 新建 | 低优先级（前端占位、无后端） |

---

## 五、草稿文件索引

以下草稿文件已生成在 `openspec/audit/drafts/` 目录下，供人工审阅：

### 更新草稿（⚠️ 不一致的 spec）

| 原文件 | 草稿路径 | 变更要点 |
|--------|---------|---------|
| `specs/employee-management.md` | `drafts/employee-management.md` | 补充 Employee 模型字段、CRUD API 路径、分页参数；标注前端尚未对接后端 |
| `specs/face-recognition.md` | `drafts/face-recognition.md` | 补充 InsightFace 模型加载、余弦相似度匹配算法、阈值配置、FaceRecord 结构；标注后端/前端人脸 API 仍为 stub |
| `specs/jenkins-cicd.md` | `drafts/jenkins-cicd.md` | 从 4 个 placeholder stage 改为 8 个 stage（6 实 + 2 占位），区分已实现与预留阶段 |
| `specs/abnormal-behavior.md` | `drafts/abnormal-behavior.md` | 更新 Constraints 为准确的"代码已实现，待模型权重文件部署"；补充安全帽检测现状；区分算法检测器（已实现）与模型检测器（planned） |
| `project.md` | `drafts/project.md` | 更新 Scope 反映真实阶段：核心 AI 管线已实现、员工/认证模块已实现、部分业务模块仍为占位 |

### 新建草稿（缺失的 spec）

| 草稿路径 | 覆盖模块 | 基于代码 |
|---------|---------|---------|
| `drafts/authentication.md` | 用户认证与权限 | `backend/apps/users/` 全部代码 |
| `drafts/camera-management.md` | 摄像头管理 | `backend/apps/cameras/` + `frontend/src/views/CamerasView.vue` |
| `drafts/ai-results.md` | AI 结果上报 | `backend/apps/ai_results/` + `ai-service/modules/backend_client.py` |
| `drafts/production-config.md` | 生产安全配置 | `backend/config/settings.py` + `Jenkinsfile` Stages 7-8 |
| `drafts/api-conventions.md` | 统一 API 响应格式 | `backend/common/response.py` |

---

> 📋 **审计完成。** 本报告及所有草稿均基于 `test-cicd` 分支的只读检查生成，未修改任何现有 spec 或业务代码。草稿中的 "待确认" 标记表示该字段/行为需要人工核实。
