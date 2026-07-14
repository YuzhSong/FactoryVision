# AIService 本地链路测试报告

测试时间：2026-07-09 09:40 (Asia/Shanghai)

当前分支：`rainy`

Git 状态摘要：
- 已保留本地前端代理改动，便于手机通过局域网访问前端并复用 `/api` 代理。
- 本轮主要修改 AIService 固定横屏处理逻辑与测试报告。
- 未提交 commit，未 push。

## 本机环境

| 项目 | 实际值 |
| --- | --- |
| OS | Windows |
| Node | `D:\DevTools\Nodejs\node.exe` |
| Python | `D:\Python314\python.exe` / `ai-service\.venv311\Scripts\python.exe` |
| Docker | 本轮未使用 |
| GPU | NVIDIA CUDA 可用，AIService 健康状态为 `cuda-yolo-frame-pipeline-ready` |
| YOLO / Helmet 模型 | 人体检测可正常加载 CUDA；头盔模型本机原缺失，已补到默认路径 `ai-service/models/helmet/helmet.pt` |

## 实际启动的服务

| 服务 | 启动命令 | 端口 / 地址 |
| --- | --- | --- |
| Frontend | `npm run dev -- --host 0.0.0.0 --port 5175` | `http://127.0.0.1:5175/monitor` |
| Backend | `python manage.py runserver 0.0.0.0:8000` | `http://127.0.0.1:8000` |
| AIService | `ai-service\.venv311\Scripts\python.exe app.py` | `http://127.0.0.1:9000` |

手机端访问地址：
- `http://192.168.1.19:5175/monitor`

## 视频链路

| 项目 | 地址 |
| --- | --- |
| 手机推流地址 | `rtmp://81.70.90.222:1935/live/1` |
| AIService 输入流 | `rtmp://81.70.90.222:1935/live/1` |
| AIService 输出流 | `rtmp://81.70.90.222:1935/live/1_detected` |
| 前端播放地址 | `webrtc://webrtc.rainycode.cn:8443/live/1_detected` |
| HTTP-FLV 播放地址 | `https://webrtc.rainycode.cn:8443/live/1_detected.flv` |
| 后端接收检测结果接口 | `POST /api/ai-results/report/` |

## 横屏手机固定摄像头模式

本轮按照固定场景处理：

1. 以后固定使用手机横屏。
2. 不再支持竖屏/横屏自动判断。
3. 不加前端旋转按钮，不加 0/90/180/270 选择器。
4. 当前真实横屏输入原始帧表现为“头在右、脚在左”。
5. AIService 在检测前固定执行：

```python
cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
```

6. 前端继续使用 `object-fit: contain`，避免拉伸。

### 当前前端样式确认

监控页当前实际样式已经满足目标：

```css
.stream-player {
  aspect-ratio: 16 / 9;
}

.stream-player video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #020617;
}
```

实测页面状态：
- 页面地址：`http://127.0.0.1:5175/monitor`
- `<video>` 播放状态：`readyState=4`
- 当前播放模式：`HTTP-FLV`
- `<video>` 实际视频尺寸：`640 x 360`
- CSS `object-fit`：`contain`
- 页面无前端控制台错误

### AIService 固定横屏处理结果

AIService `/streams/status` 实测关键字段：

```json
{
  "input_frame_shape": [1280, 720],
  "normalized_frame_shape": [720, 1280],
  "output_frame_size": [640, 360],
  "capture_fps": 30.01,
  "process_fps": 5.57,
  "processed_frames": 307
}
```

含义：
- 原始 RTMP 帧是 `1280 x 720` 的竖向像素布局。
- 固定逆时针旋转 90 度后变为 `720 x 1280`。
- 输出端按旋转后的画面生成横屏 `640 x 360`。
- 检测、画框、输出都基于旋转后的 frame。

## 实测结果

### 已验证通过

1. 手机推流到 `live/1` 后，OpenCV 可直接读到真实帧：

```text
opened=True
read_ok=True
shape=(1280, 720, 3)
```

2. AIService 已在检测前执行固定逆时针 90 度旋转。
3. 旋转后的输出尺寸已同步到 FFmpeg 输出初始化。
4. 前端监控页实际正在播放 `https://webrtc.rainycode.cn:8443/live/1_detected.flv`。
5. 前端视频未拉伸，`object-fit: contain` 生效。
6. 处理后视频流已恢复可访问，`HEAD https://webrtc.rainycode.cn:8443/live/1_detected.flv` 返回 `200`。
7. 后端 `ai_event` 数量从 `526` 增长到 `550`。
8. 最新新增事件类型为 `PERSON_DETECTION`。

### 画面与 bbox 观察

基于前端实时截图与播放器状态：
- 最终画面为横屏监控画面。
- 人物方向已恢复正常，不再是“头在右、脚在左”。
- bbox 已叠加在处理后视频上，并能跟随人物位置。

### 延迟观察

- 当前端到端延迟仍约 3-4 秒。
- 当前处理策略仍然是“只保留最新帧”，没有回退到旧帧堆积模式。
- 典型状态：
  - `capture_fps` 约 `30`
  - `process_fps` 约 `5.57`
  - `dropped_frames` 持续增长
- 说明当前仍以低延迟优先，处理不过来的旧帧会被丢弃。

## 本轮额外发现的问题

1. 如果 `reportRealtimeToBackend=true`，AIService 会调用：

```text
POST /api/realtime/frame-results/
```

但当前本地后端不存在这个接口，会返回 `404`，并导致处理线程在首帧回传实时结果时中断。

2. 为保证本轮主链路稳定，本次实测使用：

```json
"reportToBackend": true,
"reportRealtimeToBackend": false
```

这不会影响正式的 `POST /api/ai-results/report/` 入后端事件表。

## 本轮修改文件

业务/脚本文件：
- `ai-service/modules/processed_stream_service.py`
- `ai-service/app.py`
- `ai-service/tests/test_realtime_streaming.py`
- `ai-service/tests/test_app_process_stream.py`

文档：
- `docs/reports/aiservice-local-chain-test-report.md`

本地运行依赖文件：
- `ai-service/models/helmet/helmet.pt`

本轮未新增数据库迁移，未修改后端 Camera 模型，未增加旋转按钮或复杂方向配置 UI。

## 结论

固定横屏手机摄像头模式已经按本轮要求落地：

- 前端不再拉伸视频。
- AIService 已在检测前固定逆时针旋转 90 度。
- 输出宽高跟随旋转后的 frame。
- 前端能播放处理后横屏视频。
- 后端能收到 `PERSON_DETECTION` 并写入 `ai_event`。

当前仍需注意的点：
- 若后续要恢复“实时帧广播接口”，需要补齐后端 `/api/realtime/frame-results/` 或在调用侧继续保持关闭。
