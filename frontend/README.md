# Factory Vision Frontend

Vue 3 + Vite 前端，提供登录、首页看板、实时监控、告警中心、员工/人脸管理、摄像头管理、区域配置和 AI 监控日报。

## 启动与构建

从仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
npm.cmd --prefix frontend run build
```

默认开发地址为 `http://127.0.0.1:5173/`。环境变量位于 `frontend/.env`，常用配置包括 Backend API、WebSocket、WebRTC 和 HTTP-FLV 地址。

## 播放与检测开关

实时监控优先使用 WebRTC，失败时可回退 HTTP-FLV。人物框始终开启；人脸、安全帽、摔倒和区域检测开关由页面传给 Backend/AIService，并通过浏览器 `localStorage` 保存上次选择，首次默认仅开启区域检测。

业务请求统一放在 `src/api/`，页面位于 `src/views/`。接口与页面约定见 [前端设计](../docs/07-frontend-design.md)。
