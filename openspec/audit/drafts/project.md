# Factory Vision Project

> **Status:** ⚠️ Scope 描述已过时 —— 项目已从骨架阶段演进到核心管线实现阶段  
（已核实与代码一致）

---

## Overview

工厂实时视频分析监测系统面向工厂安全生产场景，采用前后端分离与 AI 独立服务架构。

## Scope

### 当前阶段：核心管线实现

项目已从初始骨架搭建阶段演进。以下模块已超出骨架/占位水平：

**已实现模块（生产代码 + 测试）：**
- 用户认证：JWT 登录/登出/me 端点 + 前端路由守卫 + 5 个测试
- 员工管理：Employee 模型 + 创建/列表 API（分页过滤）+ 5 个测试
- 人员检测：YOLO 推理 + IoU 轻量追踪器
- 人脸识别：InsightFace 模型加载 + 余弦相似度匹配（阈值可配）
- 异常行为检测：跌倒/奔跑/区域入侵三种算法检测器（纯算法，无模型依赖）
- 视频流管线：RTMP 拉流 → AI 处理 → RTMP 推流（经由 SRS 转 WebRTC）
- 前端多链路播放：WebRTC + HTTP-FLV 双链路切换
- AI 结果上报：`POST /api/ai-results/report/` 端点（校验 + 接收，不持久化）
- 统一 API 响应格式：`{code, message, data, requestId}` 全项目统一使用

**仍为占位的模块：**
- 出勤统计、事件告警、警戒区域配置（后端空 models，前端静态页面）
- 安全帽检测（无真实模型）
- 摄像头管理（后端占位，前端静态 UI）
- Docker 镜像构建与自动化部署（Jenkinsfile Stages 7-8 为占位）

### 架构约束

- 前端仅通过后端 API 获取业务数据（当前前端 EmployeesView/MonitorView 等仍使用硬编码占位数据，尚未对接后端 API）
- AI 服务仅通过后端 API 上报检测结果（`POST /api/ai-results/report/`）
- 模型权重文件（`*.pt`、`*.onnx`）不提交仓库，由运行时下载或外部提供
- AI 服务的 YOLO 模型和 InsightFace 模型加载代码已完整实现，部署阻塞项为模型权重文件和 GPU 环境

## Principles

- Keep services loosely coupled
- Prefer clear module ownership
- Drive future feature work with OpenSpec requirements first
- Spec files SHALL be updated when implementation status changes from planned to implemented

---

## Technology Stack

（版本号基于 `requirements.txt` 和 `package.json` 中的约束范围）

| 层 | 技术 |
|----|------|
| 后端 | Django 6.0 + DRF 3.16 + SimpleJWT + drf-spectacular |
| 前端 | Vue 3.5 + Vue Router 4.5 + Axios 1.11 + Vite 8 + Element Plus 2.11 + ECharts 6 |
| AI 服务 | FastAPI (>=0.116,<0.117) + Uvicorn + OpenCV 4.10 + Ultralytics 8.3 (YOLO) + InsightFace 0.7 + onnxruntime 1.20 |
| 视频流 | SRS (Simple Realtime Server) — RTMP 推流/拉流 + WebRTC 播放 |
| CI/CD | Jenkins (Declarative Pipeline) |
| 容器化 | Docker Compose (开发环境) — 生产 Dockerfile/docker-compose.prod.yml 待创建 |

---

## 变更说明

| 变更 | 原文件 | 新草稿 | 依据 |
|------|--------|--------|------|
| 更新阶段描述 | "项目骨架搭建" | "核心管线实现" | 综合代码审计：6+ 模块已实现 |
| 新增已实现模块清单 | 无 | 8 个已实现模块列表 | 逐个模块代码分析 |
| 新增仍为占位模块清单 | 无 | 5 个占位模块列表 | 逐个模块代码分析 |
| 扩展架构约束 | 3 条 | 4 条：补充模型权重不提交、代码已实现但待部署 | `.gitignore` + 代码分析 |
| 新增 Principles 第 4 条 | 3 条 | 4 条：spec 必须随实现更新 | 审计发现（spec 过时是系统性问题） |
| 新增技术栈表 | 无 | 完整技术栈（版本号已核实） | `requirements.txt` + `package.json` |
