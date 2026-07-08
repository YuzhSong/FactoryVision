# Helmet 安全帽检测对接简短指南

## 1. 需要准备什么

安全帽检测使用现成 YOLO PPE 权重，不需要自己训练。

模型来源：

```text
repo_id = Hexmon/vyra-yolo-ppe-detection
filename = best.pt
```

本项目约定模型文件放在：

```text
ai-service/models/helmet/helmet.pt
```

注意：`.pt` 权重文件被 `.gitignore` 忽略，不会提交到 git。每个同学本地运行前都需要自己下载一次，或者互相拷贝这个文件。

## 2. 安装依赖

在项目根目录执行：

```powershell
.\ai-service\.venv\Scripts\python.exe -m pip install -r ai-service\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

如果只缺下载工具，也可以单独安装：

```powershell
.\ai-service\.venv\Scripts\python.exe -m pip install -U huggingface_hub -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 3. 下载 helmet.pt

在项目根目录执行：

```powershell
.\ai-service\.venv\Scripts\python.exe -c "from pathlib import Path; from huggingface_hub import hf_hub_download; out=Path('ai-service/models/helmet'); out.mkdir(parents=True, exist_ok=True); p=Path(hf_hub_download(repo_id='Hexmon/vyra-yolo-ppe-detection', filename='best.pt', local_dir=str(out))); target=out/'helmet.pt'; target.unlink(missing_ok=True); p.replace(target); print(target.resolve())"
```

下载成功后应看到：

```text
ai-service/models/helmet/helmet.pt
```

## 4. 怎么接入现有链路

现有链路已经接好了，不需要推流同学额外处理安全帽模型。

调用流程是：

```text
FrameProcessor.process_frame()
-> PersonDetector.detect()
-> HelmetDetector.detect()
-> AbnormalBehaviorService.build_ai_report()
-> 输出 PERSON_DETECTION / HELMET_WARNING
```

也就是说，只要其他同学调用已有的帧检测接口或视频处理链路，头盔检测会自动参与：

```text
POST /detect/frame
POST /process/stream
POST /streams/start
```

头盔检测会先识别 `Hardhat` / `NO-Hardhat`，再根据安全帽框中心点匹配到对应人员 `trackId`。如果识别到未戴安全帽并超过告警阈值，会输出：

```json
{
  "type": "HELMET_WARNING",
  "trackId": "t-1",
  "helmetStatus": "no_helmet",
  "confidence": 0.88,
  "level": "high"
}
```

## 5. 可调配置

默认配置在 `ai-service/ai_config.py`：

```text
HELMET_MODEL_PATH=ai-service/models/helmet/helmet.pt
HELMET_DEVICE=auto
HELMET_IMAGE_SIZE=640
HELMET_CONFIDENCE_THRESHOLD=0.35
HELMET_IOU_THRESHOLD=0.45
HELMET_WARNING_THRESHOLD=0.6
```

`HELMET_DEVICE=auto` 会优先使用 CUDA。RTX 4060 环境下，测试中已自动走到 `cuda:0`。

如果需要强制 CPU：

```powershell
$env:HELMET_DEVICE="cpu"
```

如果需要强制 GPU：

```powershell
$env:HELMET_DEVICE="cuda:0"
```

## 6. 怎么测试

先跑头盔模型烟测：

```powershell
.\ai-service\.venv\Scripts\python.exe ai-service\scripts\check_helmet_yolo.py
```

成功时会输出模型路径、设备和类别名，例如：

```text
device=cuda:0
classNames={..., 3: 'Hardhat', 8: 'NO-Hardhat', ...}
```

如果要用真实图片测试：

```powershell
.\ai-service\.venv\Scripts\python.exe ai-service\scripts\check_helmet_yolo.py --image D:\path\to\test.jpg
```

再跑 ai-service 单测：

```powershell
cd ai-service
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 7. 常见问题

如果报 `Helmet model not found`，说明没有下载 `helmet.pt`，按第 3 步下载即可。

如果报 `huggingface_hub` 不存在，说明依赖没装全，按第 2 步安装。

如果直接 import `ultralytics` 报用户目录权限问题，优先通过 ai-service 的脚本或服务入口运行，因为 `ai_config.py` 已经把 Ultralytics 缓存目录重定向到了项目内。

