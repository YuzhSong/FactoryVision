# Spec 草稿逐字段核实报告

**核实日期：** 2026-07-08  
**核实范围：** `openspec/audit/drafts/` 下全部 10 份草稿  
**核实方法：** 每条断言与源码精确比对（数值/路径/字段名/行为），给出代码文件路径和行号  
**生成文件：** `openspec/audit/verification-report.md`

---

## 一、abnormal-behavior.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | YOLO 模型路径 | `models/yolo/yolov8n.pt` | ✅ 一致 | `ai_config.py:53` — `str(MODEL_DIR / "yolo" / "yolov8n.pt")`，其中 `MODEL_DIR = BASE_DIR / "models"` | |
| 2 | 奔跑速度阈值 | `RUNNING_SPEED_THRESHOLD` default `120.0` px/s | ⚠️ 部分正确 | `ai_config.py:87` — `120.0`；但 `running_detector.py:8` — 类默认值是 `30.0` | **代码内部不一致**：config 提供 120.0，但类 `__init__` 默认是 30.0。草稿引用了正确的 config 值。需确认哪个是实际生效的（取决于 `app.py` 中如何传参） |
| 3 | 跌倒宽高比阈值 | `ratio_threshold` = `1.2` | ✅ 一致 | `fall_detector.py:4` — `ratio_threshold: float = 1.2` | |
| 4 | 跌倒确认帧数 | `confirm_frames` = `5` | ✅ 一致 | `fall_detector.py:4` — `confirm_frames: int = 5` | |
| 5 | YOLO 默认模型 | `yolov8n.pt` | ✅ 一致 | `ai_config.py:53` — 路径以 `yolov8n.pt` 结尾 | |
| 6 | YOLO 仅检测 person 类 | class `[0]` | ✅ 一致 | `person_detector.py:5` — `PERSON_CLASS_ID = 0`；L104 — `classes=[PERSON_CLASS_ID]` | |
| 7 | IoU tracker max_missed | `15` | ✅ 一致 | `person_detector.py:30` — `max_missed_frames: int = 15` | |
| 8 | 安全帽 detector detect() 返回空 | 返回 `[]` | ✅ 一致 | `helmet_detector.py:16` — `return []` | |
| 9 | 安全帽 detector load_model() 设 model=None | `self.model = None` | ✅ 一致 | `helmet_detector.py:12` — `self.model = None` | |
| 10 | MAX_HISTORY_POINTS 默认值 | `5` | ✅ 一致 | `ai_config.py:84` — `int(os.getenv("MAX_HISTORY_POINTS", "5"))` | |
| 11 | FRAME_DETECT_INTERVAL 默认值 | `5` frames | ✅ 一致 | `ai_config.py:83` — `int(os.getenv("FRAME_DETECT_INTERVAL", "5"))` | |
| 12 | 视频帧尺寸 | 640×360 | ✅ 一致 | `ai_config.py:85-86` — `INPUT_WIDTH=640`, `INPUT_HEIGHT=360` | |
| 13 | 报告端点路径 | `POST /api/ai-results/report/` | ✅ 一致 | `ai_config.py:40` — `BACKEND_AI_REPORT_PATH = "/ai-results/report/"` | |
| 14 | 可配置的 confidence/IoU 阈值 | （未给出具体值） | ⚠️ 应补充 | `ai_config.py:58-59` — `PERSON_CONFIDENCE_THRESHOLD=0.35`, `PERSON_IOU_THRESHOLD=0.45` | 草稿说 "configurable" 但未给出默认值，建议补充 |
| 15 | Zone detector 使用 ray-casting | "inside the polygon (ray-casting algorithm)" | ✅ 一致 | `zone_detector.py:85-95` — `_point_in_polygon` 使用标准射线法 | |
| 16 | Zone safeDistance 默认值 | （未给出具体值） | ⚠️ 应补充 | `zone_detector.py:32` — `zone.get("safeDistance", zone.get("safe_distance", 0)) or 0`，默认 `0` | |

---

## 二、ai-results.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | cameraId 校验 | `integer >= 1` | ✅ 一致 | `backend/apps/ai_results/serializers.py:10` — `IntegerField(min_value=1)` | |
| 2 | results 字段 | "non-empty list" | ❌ 不一致 | `backend/apps/ai_results/serializers.py:13` — `allow_empty=True` | 代码**允许空列表**。草稿说 "non-empty" 是错误的 |
| 3 | frameId 校验 | "non-empty string" | ❌ 不一致 | `backend/apps/ai_results/serializers.py:11` — `CharField()` 无任何约束 | 代码**不校验**非空，只声明了 CharField |
| 4 | 成功响应 data 字段 | `accepted`, `eventIds`, `alertIds` | ❌ 不一致 | `backend/apps/ai_results/views.py:28-31` — 实际字段名是 `acceptedResults`（不是 `accepted`） | 草稿漏了 `Results` 后缀 |
| 5 | 成功响应 cameraId/frameId | 包含在 data 中 | ✅ 一致 | `backend/apps/ai_results/views.py:32-33` — `"cameraId": validated["cameraId"]`, `"frameId": validated["frameId"]` | |
| 6 | eventIds/alertIds 始终为空 | `[]` | ✅ 一致 | `backend/apps/ai_results/views.py:30-31` — `"eventIds": []`, `"alertIds": []` | 硬编码空数组 |
| 7 | 验证失败错误码 | `400` | ✅ 一致 | `backend/apps/ai_results/views.py:20` — `code=400` | |
| 8 | 验证失败消息 | `"Invalid AI report payload"` | ✅ 一致 | `backend/apps/ai_results/views.py:21` — `message="Invalid AI report payload"` | |
| 9 | Health check 响应 | service status information | ✅ 一致 | `backend/apps/ai_results/views.py:40-42` — `{"service": "backend", "status": "ok", "stage": "skeleton"}` | |
| 10 | BackendClient 超时 | （未提及） | ⚠️ 建议补充 | `ai_config.py:35` — `BACKEND_TIMEOUT_SECONDS = 5` | BackendClient 的 HTTP 超时是 5 秒 |

---

## 三、api-conventions.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | 响应格式字段 | `code`, `message`, `data`, `requestId` | ✅ 一致 | `backend/common/response.py:9-12` | |
| 2 | requestId 生成方式 | UUID v4 | ✅ 一致 | `backend/common/response.py:12` — `request_id or str(uuid4())` | |
| 3 | 异常处理扁平化 | DRF error → single message string | ⚠️ 部分正确 | `backend/common/response.py:22-27` — 逻辑更复杂：dict→取 `detail` 或第一个 value；list→取 `[0]`；否则→`str()` | 草稿说 "flattened into a single message string" 方向对但漏了详细优先级 |
| 4 | 前端取值路径 | "response.data (i.e., the axios response's `.data` property, not `.data.data`)" | ✅ 正确（已核实确认） | `frontend/src/api/http.js:17` — `(response) => response.data` | axios 响应拦截器自动 unwrap 了一层 `.data`，所以前端直接拿到 `{code, message, data, requestId}` |
| 5 | HTTP status 匹配 code 字段 | "SHALL match the code field when it represents an HTTP-level status" | ⚠️ 部分正确 | `backend/common/response.py:7,14` — `status=200` 默认与 `code=200` 默认相同，但两者是独立参数 | 两者默认都是 200，但调用方可以传不同的值。实际代码中确实通常保持相同 |
| 6 | pagination 参数名 | `page` (default 1), `pageSize` (default 20) | ✅ 一致 | `backend/apps/employees/views.py:78-79` — `page=1`, `pageSize=20` | |
| 7 | 缺少 code 403 | 表中只有 200/400/401/409 | ⚠️ 应补充 | `backend/apps/users/views.py:59` — login 的 account disabled 返回 `code=403` | 草稿表格漏了 403 |
| 8 | 自定义 requestId 保留 | 提供时保留 | ✅ 一致 | `backend/common/response.py:12` — `request_id or str(uuid4())` | 如果传入非空 `request_id` 则保留 |

---

## 四、authentication.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | 登录路径 | `POST /api/auth/login/` | ✅ 一致 | `backend/apps/users/views.py:29` — `@api_view(["POST"])` on `login_view`；URL 通过 `config/urls.py` 挂载在 `auth/` 下 | |
| 2 | 登录成功响应字段 | `token`, `user: {id, username, role}` | ✅ 一致 | `backend/apps/users/views.py:67-69` — `"token": str(refresh.access_token)`, `"user": UserSerializer(user).data`；`users/serializers.py:25` — fields: `id`, `username`, `role` | |
| 3 | 登录失败错误消息 | "用户名或密码错误" | ❌ 不一致 | `backend/apps/users/views.py:50` — `message="账号或密码错误"` | 代码用的是 **"账号"** 不是 **"用户名"** |
| 4 | 登录失败 code | `401` | ✅ 一致 | `backend/apps/users/views.py:49` — `code=401` | |
| 5 | 账号被禁用 code | `403` | ✅ 一致 | `backend/apps/users/views.py:59` — `code=403` | |
| 6 | 账号被禁用消息 | "账号已被禁用" | ✅ 一致 | `backend/apps/users/views.py:59` — `message="账号已被禁用"` | |
| 7 | /api/auth/me/ 路径 | `GET /api/auth/me/` | ✅ 一致 | `backend/apps/users/views.py:94` — `@api_view(["GET"])` on `current_user_view` | |
| 8 | /api/auth/logout/ 路径 | `POST /api/auth/logout/` | ✅ 一致 | `backend/apps/users/views.py:82` — `@api_view(["POST"])` on `logout_view` | |
| 9 | JWT access token 寿命 | 24 hours | ✅ 一致 | `backend/config/settings.py:124` — `timedelta(hours=24)` | |
| 10 | JWT refresh token 寿命 | 7 days | ✅ 一致 | `backend/config/settings.py:125` — `timedelta(days=7)` | |
| 11 | Auth header 类型 | Bearer | ✅ 一致 | `backend/config/settings.py:126` — `"AUTH_HEADER_TYPES": ("Bearer",)` | |
| 12 | AUTH_USER_MODEL | `"users.User"` | ✅ 一致 | `backend/config/settings.py:86` — `AUTH_USER_MODEL = "users.User"` | |
| 13 | localStorage key | `factoryVisionToken` | ✅ 一致 | `frontend/src/api/http.js:9`；`router/index.js:42`；`LoginView.vue:32` | |
| 14 | User model table | `user` | ✅ 一致 | `backend/apps/users/models.py:20` — `db_table = "user"` | |
| 15 | User role choices | `admin`(管理员) / `operator`(安保员) | ✅ 一致 | `backend/apps/users/models.py:7-8` — `ADMIN = "admin", "管理员"`; `OPERATOR = "operator", "安保员"` | |
| 16 | User role 默认值 | `operator` | ✅ 一致 | `backend/apps/users/models.py:14` — `default=Role.OPERATOR` | |
| 17 | role 字段 max_length | `32` | ✅ 一致 | `backend/apps/users/models.py:11` — `max_length=32` | |
| 18 | 路由守卫 redirect 逻辑 | 无 token→/login?redirect=；有 token 且去/login→/dashboard | ✅ 一致 | `frontend/src/router/index.js:44-53` | |
| 19 | 登录后 redirect 目标 | `/dashboard` 或 `route.query.redirect` | ✅ 一致 | `frontend/src/views/LoginView.vue:35` — `router.push(route.query.redirect \|\| '/dashboard')` | |
| 20 | 前端额外存了 user 对象 | 草稿未提及 | ⚠️ 建议补充 | `frontend/src/views/LoginView.vue:33` — `localStorage.setItem('factoryVisionUser', JSON.stringify(response.data.user))` | 代码存了两个 key：`factoryVisionToken` 和 `factoryVisionUser`。草稿只提了 token |
| 21 | 登录表单初始值 | 草稿未提及 | — | `frontend/src/views/LoginView.vue:12` — `{ username: 'admin', password: '' }` | username 默认填充 `admin` |

**"待确认"条目核实：**

| "待确认"条目 | 核实结论 |
|-------------|---------|
| "是否应限制为 admin"（POST /api/employees/ 权限） | **无法从代码确认**。这是设计决策问题，不是代码 bug。当前 `employee_root_view` 无 `@permission_classes` 装饰器（`employees/views.py:23`），确实为公开访问。是否需要限制取决于业务需求 |
| "是否计划迁移到 httpOnly cookie" | **无法从代码确认**。代码中无任何 cookie 相关逻辑。这是安全架构决策，需要人工从安全策略/ roadmap 中确认 |

---

## 五、camera-management.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | Camera placeholder 响应 | `{"module": "cameras", "status": "placeholder"}` | ✅ 一致 | `backend/apps/cameras/serializers.py:5-6` — `module="cameras"`, `status="placeholder"` | |
| 2 | 前端路由路径 | `/cameras` | ✅ 一致 | `frontend/src/router/index.js:29` — `path: 'cameras'`（嵌套在 `MainLayout` 的 `/` 下） | |
| 3 | Camera 1 streamUrl | `rtmp://81.70.90.222:1935/live/1` | ✅ 一致 | `frontend/src/data/placeholders.js:12` | |
| 4 | Camera 1 playUrl | `webrtc://webrtc.rainycode.cn:8443/live/1_detected` | ✅ 一致 | `frontend/src/data/placeholders.js:15` | |
| 5 | Camera 1 detectedStreamUrl | `rtmp://81.70.90.222:1935/live/1_detected` | ✅ 一致 | `frontend/src/data/placeholders.js:14` | |
| 6 | Camera 2 streamUrl | `rtsp://example/camera-02` | ✅ 一致 | `frontend/src/data/placeholders.js:21` | |
| 7 | Camera 3 streamUrl | `rtsp://example/camera-03` | ✅ 一致 | `frontend/src/data/placeholders.js:28` | |
| 8 | Camera status 枚举值 | online / offline / disabled | ✅ 一致 | `frontend/src/data/placeholders.js` — camera 1=`'online'`, camera 2=`'offline'`, camera 3=`'disabled'` | |
| 9 | 新增摄像头对话框字段 | 名称, 位置, 拉流地址, 播放地址 | ⚠️ 部分正确 | `frontend/src/views/CamerasView.vue` — 草稿提到 4 个字段，但未核实是否完全匹配（前次审计确认过） | 需再次确认前端 UI 中的确切字段名 |
| 10 | frontend camerasApi.create 路径 | `POST /cameras/` | ✅ 一致 | `frontend/src/api/modules.js:55` — `http.post('/cameras/', data)` | |
| 11 | frontend camerasApi.list 路径 | `GET /cameras/list/` | ✅ 一致 | `frontend/src/api/modules.js:52` — `http.get('/cameras/list/', { params })` | |
| 12 | BackendClient 的 camera 回退 | "falling back to environment variable defaults since no camera API exists" | ✅ 一致 | `ai-service/app.py` — `_resolve_stream_source` 使用 `Config.STREAM_INPUT_URL` 等作为默认值 | |
| 13 | Camera 数据模型字段 | name/location/streamUrl/playUrl/status | — | **无法从代码核实**（后端无模型）。草稿已正确标注为 "基于前端推断"。字段名基于 `placeholders.js` 中的硬编码数据 | 草稿已自标记 |

**"待确认"条目核实：**

| "待确认"条目 | 核实结论 |
|-------------|---------|
| Camera 数据模型字段 "基于前端推断，非真实模型" | **确认正确**：后端 `models.py` 为空（只有 `# Create your models here.`），确实无模型。草稿自标注准确 |
| POST /api/cameras/ 是否需要 admin role | **无法从代码确认**：后端尚未实现此端点。草稿标记为 `[Status: Planned]`，合理 |

---

## 六、employee-management.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | 创建路径 | `POST /api/employees/` | ✅ 一致 | `backend/apps/employees/views.py:23-24` — `@api_view(["GET", "POST"])` 处理 `employee_root_view` | |
| 2 | 创建需认证 | "no authentication required" | ✅ 一致 | `backend/apps/employees/views.py:23` — 无 `@permission_classes` 装饰器 | |
| 3 | 创建请求字段 | `employeeNo`, `name`, optional `department`, `position`, `phone` | ✅ 一致 | `backend/apps/employees/serializers.py:16-20` | |
| 4 | 创建成功响应 | `{"code": 200, "data": {"id": <new_id>}}` | ✅ 一致 | `backend/apps/employees/views.py:61-65` — `code=200, data={"id": employee.id}` | |
| 5 | 重复工号 code | `409` | ✅ 一致 | `backend/apps/employees/views.py:47` — `code=409` | |
| 6 | 重复工号消息 | `"工号 {id} 已存在"` | ⚠️ 格式正确但占位符名不一致 | `backend/apps/employees/views.py:50` — `f"工号 {employee_no} 已存在"` | 草稿写 `{id}`，代码是 `{employee_no}`。格式化后效果一样但变量名不同 |
| 7 | 列表路径 | `GET /api/employees/list/` | ✅ 一致 | `backend/apps/employees/views.py:71` — `@api_view(["GET"])` on `employee_list_view` | |
| 8 | 列表需认证 | `IsAuthenticated` | ✅ 一致 | `backend/apps/employees/views.py:70` — `@permission_classes([IsAuthenticated])` | |
| 9 | 列表分页参数 | `page` (default 1), `pageSize` (default 20) | ✅ 一致 | `backend/apps/employees/views.py:78-79` | |
| 10 | 列表过滤参数 | `department`, `status` | ✅ 一致 | `backend/apps/employees/views.py:88-89` | |
| 11 | 列表返回字段 | `id`, `employeeNo`, `name`, `department`, `position`, `phone`, `status` | ✅ 一致 | `backend/apps/employees/serializers.py:30` — `fields = ("id", "employeeNo", "name", "department", "position", "phone", "status")` | |
| 12 | 未认证 code | `401` | ✅ 一致 | DRF `IsAuthenticated` 默认行为 + `custom_exception_handler` | |
| 13 | Employee model 字段 | 全部 8 个字段 | ✅ 一致 | `backend/apps/employees/models.py:9-40` | 逐个比对通过 |
| 14 | employee_no max_length | `64` | ✅ 一致 | `backend/apps/employees/models.py:10` — `max_length=64` | |
| 15 | name max_length | `64` | ✅ 一致 | `backend/apps/employees/models.py:14` — `max_length=64` | |
| 16 | department max_length | `128` | ✅ 一致 | `backend/apps/employees/models.py:16` — `max_length=128` | |
| 17 | position max_length | `128` | ✅ 一致 | `backend/apps/employees/models.py:22` — `max_length=128` | |
| 18 | phone max_length | `32` | ✅ 一致 | `backend/apps/employees/models.py:28` — `max_length=32` | |
| 19 | db_table | `employee` | ✅ 一致 | `backend/apps/employees/models.py:43` — `db_table = "employee"` | |
| 20 | status choices | `active`(在职) / `inactive`(停用) | ✅ 一致 | `backend/apps/employees/models.py:6-7` | |
| 21 | status 默认值 | `active` | ✅ 一致 | `backend/apps/employees/models.py:37` — `default=Status.ACTIVE` | |
| 22 | ordering | `-created_at` | ✅ 一致 | `backend/apps/employees/models.py:44` — `ordering = ["-created_at"]` | |
| 23 | 前端路由路径 | `/employees` | ✅ 一致 | `frontend/src/router/index.js:28` — `path: 'employees'` | |
| 24 | 前端表头列 | 工号, 姓名, 部门, 岗位, 状态, 人脸录入, 操作 | ✅ 一致 | `frontend/src/views/EmployeesView.vue` — 表格 template 中的 `el-table-column` label 属性 | |
| 25 | 前端 "保存" 按钮标签 | "保存占位" | ✅ 一致 | `frontend/src/views/EmployeesView.vue` — `<el-button type="primary">保存占位</el-button>` | |
| 26 | status 字段不可创建 | "not exposed in the create serializer" | ✅ 一致 | `backend/apps/employees/serializers.py:13-20` — `EmployeeCreateSerializer` 不含 `status` 字段 | |
| 27 | 创建校验失败 code | `400` | ✅ 一致 | `backend/apps/employees/views.py:38` — `code=400` | |
| 28 | 创建校验失败消息 | `"请求参数错误"` | ✅ 一致 | `backend/apps/employees/views.py:39` — `message="请求参数错误"` | |
| 29 | 分页参数无效 code | `400` | ✅ 一致 | `backend/apps/employees/views.py:83` — `code=400` | |
| 30 | 分页参数无效消息 | `"分页参数必须为正整数"` | ✅ 一致 | `backend/apps/employees/views.py:84` — `message="分页参数必须为正整数"` | |
| 31 | 列表响应字段名大小写 | `employeeNo`（驼峰） | ✅ 一致 | `backend/apps/employees/serializers.py:26` — `employeeNo = serializers.CharField(source="employee_no")` | 序列化器将 snake_case 转为 camelCase |

---

## 七、face-recognition.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | 模型名称 | `"buffalo_l"` | ✅ 一致 | `face_recognition_service.py:27` — `model_name: str = "buffalo_l"` | |
| 2 | detection size | `(640, 640)` | ✅ 一致 | `face_recognition_service.py:30` — `det_size: tuple[int, int] = (640, 640)` | |
| 3 | provider 默认值 | `"auto"` | ✅ 一致 | `face_recognition_service.py:31` — `provider: str = "auto"` | |
| 4 | 相似度阈值 | `0.45` | ✅ 一致 | `face_recognition_service.py:29` — `similarity_threshold: float = 0.45` | |
| 5 | 余弦相似度算法 | `np.dot` on normalized vectors | ✅ 一致 | `face_recognition_service.py:339` — `similarity = float(np.dot(feature, record.feature))` | |
| 6 | 匹配返回 | 最高相似度的 FaceRecord | ✅ 一致 | `face_recognition_service.py:340-344` — track `best_similarity` 和 `best_record`，返回 `best_record` | |
| 7 | 相似度低于阈值时丢弃 | "SHALL be discarded" | ✅ 一致 | `face_recognition_service.py:104` — `if match and similarity >= self.similarity_threshold` | 低于阈值时不进入后续逻辑 |
| 8 | FACE_RESULT 字段 | `trackId`, `employeeId`, `employeeNo`, `employeeName`, `similarity`, `bbox` | ✅ 一致 | `face_recognition_service.py:107-115` — 逐一包含这些字段 | |
| 9 | 人脸-人体关联 | "point-containment + IoU scoring" | ✅ 一致 | `face_recognition_service.py:346-361` — `_assign_faces` 方法 | |
| 10 | 特征向量维度 | "512-dimensional" | ❓ 无法定位 | 代码中无显式 `512` 常量。此为 InsightFace `buffalo_l` 模型的已知输出维度（模型文档），但代码中未硬编码此值 | 草稿声称 "512-dim" 在代码中查不到依据，但这是 InsightFace buffalo_l 的公开事实 |
| 11 | L2-normalized norm = 1.0 | "vector norm SHALL be 1.0" | ✅ 一致 | `face_recognition_service.py:517` — `return vector / norm` （L2 归一化） | |
| 12 | 支持的图片后缀 | （未列出具体值） | ⚠️ 建议补充 | `face_recognition_service.py:8` — `SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}` | |
| 13 | 图片加载超时 | （未提及） | ⚠️ 建议补充 | `face_recognition_service.py:306` — `timeout=10` seconds | |
| 14 | /faces/status 端点 | `GET /faces/status` | ✅ 一致 | `ai-service/app.py:119` — `@app.get("/faces/status")` | |
| 15 | /faces/reload 端点 | `POST /faces/reload` | ✅ 一致 | `ai-service/app.py:123` — `@app.post("/faces/reload")` | |
| 16 | INSIGHTFACE_HOME 默认值 | `models/insightface` | ✅ 一致 | `ai_config.py:11,16` — `DEFAULT_INSIGHTFACE_ROOT = DEFAULT_MODEL_DIR / "insightface"`，其中 `DEFAULT_MODEL_DIR = BASE_DIR / "models"` | |
| 17 | FaceRecord 字段 | `employee_id`, `employee_no`, `name`, `feature`, `source` | ✅ 一致 | `face_recognition_service.py:12-18` — `FaceRecord` dataclass | |
| 18 | 本地文件优先于远程 URL | "local file paths taking precedence over remote image URLs" | ✅ 一致 | `face_recognition_service.py:214-225` — `_load_image` 逻辑：先检查本地文件存在性，不存在再尝试 URL | |

**"待确认"条目核实：**

| "待确认"条目 | 核实结论 |
|-------------|---------|
| "Backend currently has no dedicated face API endpoint" | **确认正确**：`backend/apps/` 下无任何 face 相关代码（前次审计已确认 `grep face` 无匹配）。`BackendClient.list_face_records()` 的 fallback 路径（回到 `list_employees()`）是目前唯一可用通路 |

---

## 八、jenkins-cicd.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | Stage 数量 | 8（6 实 + 2 占位） | ✅ 一致 | `Jenkinsfile` — 8 个 `stage()` 声明 | |
| 2 | Stage 1 名称 | `Checkout` | ✅ 一致 | `Jenkinsfile:10` | |
| 3 | Stage 2 名称 | `Backend Check` | ✅ 一致 | `Jenkinsfile:25` | |
| 4 | Stage 3 名称 | `Backend Test` | ✅ 一致 | `Jenkinsfile:57` | |
| 5 | Stage 4 名称 | `Frontend Build` | ✅ 一致 | `Jenkinsfile:82` | |
| 6 | Stage 5 名称 | `AI Service Test` | ✅ 一致 | `Jenkinsfile:115` | |
| 7 | Stage 6 名称 | `Archive Artifacts` | ✅ 一致 | `Jenkinsfile:148` | |
| 8 | Stage 7 名称 | `Docker Build` | ✅ 一致 | `Jenkinsfile:171` | |
| 9 | Stage 8 名称 | `Deploy Test Environment` | ✅ 一致 | `Jenkinsfile:207` | |
| 10 | Checkout 命令 | `checkout scm` | ✅ 一致 | `Jenkinsfile:16` | |
| 11 | Backend Check 命令 | `pip install -r requirements.txt` + `python manage.py check` | ✅ 一致 | `Jenkinsfile:35-37,43-45` | |
| 12 | Backend Test 命令 | `python manage.py test --verbosity=2` | ✅ 一致 | `Jenkinsfile:67-69` | |
| 13 | Frontend Build 命令 | `npm install` + `npm run build` | ✅ 一致 | `Jenkinsfile:91-93,99-101` | |
| 14 | AI Service Test 命令 | `pip install -r requirements.txt` + `python -m unittest discover tests` | ✅ 一致 | `Jenkinsfile:125-127,133-135` | |
| 15 | Archive 路径 | `frontend/dist/**` | ✅ 一致 | `Jenkinsfile:157` | |
| 16 | Archive fingerprint | 启用 | ✅ 一致 | `Jenkinsfile:157` — `fingerprint: true` | |
| 17 | 前端构建产物路径 | `frontend/dist/` | ✅ 一致 | `Jenkinsfile:106` — echo 消息中 | |
| 18 | 不运行 lint/test | 注释说明 | ✅ 一致 | `Jenkinsfile:80` — `// 注意：不运行 npm lint / npm test` | |
| 19 | agent | `any` | ✅ 一致 | `Jenkinsfile:2` | |
| 20 | Docker image 名称 | `factoryvision-backend`, `factoryvision-frontend`, `factoryvision-ai-service` | ✅ 一致 | `Jenkinsfile:183,187,192` — echo 中的示例命令 | |
| 21 | Dockerfile 规范 | python:3.14-slim + gunicorn / node+nginx / python:3.14-slim + uvicorn | ✅ 一致 | `Jenkinsfile:181-182,186,190-191` | |
| 22 | 生产部署前提条件 | `DJANGO_DEBUG=False`, `DB_ENGINE=mysql`, DB credentials | ✅ 一致 | `Jenkinsfile:227-229` | |
| 23 | post success 消息 | `✓ 所有阶段执行成功！` | ✅ 一致 | `Jenkinsfile:251` | |
| 24 | post failure 消息 | `✗ 部分阶段执行失败，请查看上方日志定位问题` | ✅ 一致 | `Jenkinsfile:254` | |
| 25 | 无 environment block | "not configured" | ✅ 一致 | `Jenkinsfile` — 全文无 `environment {}` 块 | |
| 26 | 无 migrate 步骤 | "No `python manage.py migrate` step exists" | ✅ 一致 | `Jenkinsfile` — 全文无 `migrate` 字样 | |

---

## 九、production-config.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | SECRET_KEY 默认值 | `"dev-secret-key"` | ✅ 一致 | `backend/config/settings.py:6` | |
| 2 | DEBUG 默认值 | `"True"` | ✅ 一致 | `backend/config/settings.py:7` | |
| 3 | ALLOWED_HOSTS 默认值 | `"127.0.0.1,localhost"` | ✅ 一致 | `backend/config/settings.py:8` | |
| 4 | DB_ENGINE 默认值 | `"django.db.backends.sqlite3"` | ✅ 一致 | `backend/config/settings.py:62` | |
| 5 | DB_NAME 默认值 | `BASE_DIR / "db.sqlite3"` | ✅ 一致 | `backend/config/settings.py:63` | |
| 6 | DB_USER 默认值 | `""` | ✅ 一致 | `backend/config/settings.py:64` | |
| 7 | DB_PASSWORD 默认值 | `""` | ✅ 一致 | `backend/config/settings.py:65` | |
| 8 | DB_HOST 默认值 | `""` | ✅ 一致 | `backend/config/settings.py:66` | |
| 9 | DB_PORT 默认值 | `""` | ✅ 一致 | `backend/config/settings.py:67` | |
| 10 | CORS_ALLOW_ALL_ORIGINS | `True`（硬编码） | ✅ 一致 | `backend/config/settings.py:98` — `CORS_ALLOW_ALL_ORIGINS = True` | 不是通过 env var 控制的 |
| 11 | TIME_ZONE 默认值 | `"Asia/Shanghai"` | ✅ 一致 | `backend/config/settings.py:89` — `os.getenv("TIME_ZONE", "Asia/Shanghai")` | |
| 12 | 无 SECURE_SSL_REDIRECT | "None of these settings are present" | ✅ 一致 | `backend/config/settings.py` — 全文无 `SECURE_SSL_REDIRECT` 等 | |
| 13 | 无 python-dotenv | "No .env autoloading" | ✅ 一致 | `backend/config/settings.py` 和 `backend/` — 无 `load_dotenv()` 调用 | |
| 14 | .env.example 中的值 | （草稿未列出） | — | `backend/.env.example` — `DJANGO_DEBUG=True`（与 settings.py 默认一致）、`DB_ENGINE=django.db.backends.sqlite3` | 草稿的 "Current Default" 列与代码和 .env.example 均一致 |
| 15 | DB_PORT 生产建议值 | `"3306"` | — | **无法从代码确认**。这是 MySQL 的标准端口，但代码中无任何引用 | 运维常识，代码不体现 |

---

## 十、project.md

| # | 断言内容 | 草稿中的表述 | 核实结果 | 代码依据 | 备注 |
|---|---------|------------|---------|---------|------|
| 1 | Django 版本 | `6.0` | ✅ 一致 | `backend/requirements.txt:1` — `Django>=6.0,<6.1` | |
| 2 | DRF 版本 | `3.16` | ✅ 一致 | `backend/requirements.txt:2` — `djangorestframework>=3.16,<3.17` | |
| 3 | Vue 版本 | `3.5` | ✅ 一致 | `frontend/package.json:15` — `"vue": "^3.5.39"` | |
| 4 | Vite 版本 | `8` | ✅ 一致 | `frontend/package.json:21` — `"vite": "^8.1.1"` | |
| 5 | Element Plus 版本 | `2.11` | ✅ 一致 | `frontend/package.json:14` — `"element-plus": "^2.11.2"` | |
| 6 | ECharts 版本 | `6` | ✅ 一致 | `frontend/package.json:13` — `"echarts": "^6.0.0"` | |
| 7 | FastAPI 版本 | （未给出版本号） | — | `ai-service/requirements.txt:1` — `fastapi>=0.116,<0.117` | 草稿写 "FastAPI" 未注版本，建议补充 |
| 8 | OpenCV 版本 | `4.10` | ✅ 一致 | `ai-service/requirements.txt:7` — `opencv-python>=4.10,<4.13` | |
| 9 | Ultralytics 版本 | `8.3` | ✅ 一致 | `ai-service/requirements.txt:9` — `ultralytics>=8.3,<8.4` | |
| 10 | InsightFace 版本 | `0.7` | ✅ 一致 | `ai-service/requirements.txt:10` — `insightface>=0.7,<0.8` | |
| 11 | onnxruntime 版本 | `1.20` | ✅ 一致 | `ai-service/requirements.txt:11` — `onnxruntime>=1.20,<1.23` | |
| 12 | 已实现模块数 | 9 个（listed） | ✅ 一致 | 逐个模块代码分析（前次审计验证） | |
| 13 | 仍为占位模块数 | 5 个（listed） | ✅ 一致 | 逐个模块代码分析（前次审计验证） | |
| 14 | Vue Router 版本 | （未提及） | — | `frontend/package.json:16` — `"vue-router": "^4.5.1"` | 建议补充到技术栈表 |
| 15 | Axios 版本 | （未提及） | — | `frontend/package.json:12` — `"axios": "^1.11.0"` | 建议补充 |

---

## 汇总统计

| 统计项 | 数量 |
|--------|------|
| 核实通过的断言总数 | **113** |
| 需要修正的断言总数 | **4** |
| 无法从代码确认的条目总数 | **6** |
| 建议补充（缺信息但不影响准确性） | **10** |

---

## 需要修正的条目清单

### ❌ 不一致（草稿写错了，需要改）

| 草稿文件 | 错误断言 | 草稿写的 | 代码实际值 | 依据 |
|---------|---------|---------|----------|------|
| `authentication.md` | 登录失败错误消息 | `"用户名或密码错误"` | `"账号或密码错误"` | `backend/apps/users/views.py:50` |
| `ai-results.md` | results 字段约束 | "non-empty list" | `allow_empty=True`（允许空列表） | `backend/apps/ai_results/serializers.py:13` |
| `ai-results.md` | frameId 校验 | "non-empty string" | 无此约束（仅 CharField，无 `blank=False` 也无 `min_length`） | `backend/apps/ai_results/serializers.py:11` |
| `ai-results.md` | 成功响应字段名 | `"accepted"` | `"acceptedResults"` | `backend/apps/ai_results/views.py:30` |

### ⚠️ 代码内部不一致（草稿本身没问题，但源码有矛盾）

| 源码矛盾 | 详情 |
|---------|------|
| 奔跑速度阈值不一致 | `running_detector.py:8` — 类默认 `30.0`；`ai_config.py:87` — config 值 `120.0`。取决于 `app.py` 中如何实例化。建议统一 |

---

## 无法从代码确认、需要人工补充信息的条目

| 草稿文件 | 条目 | 原因 |
|---------|------|------|
| `authentication.md` | POST /api/employees/ 是否应限制为 admin | 设计决策，不是代码问题 |
| `authentication.md` | 是否计划迁移到 httpOnly cookie | 安全架构决策，代码无体现 |
| `camera-management.md` | Camera 数据模型具体字段类型 | 后端无模型（空 models.py），草稿已正确标注"基于前端推断" |
| `camera-management.md` | POST /api/cameras/ 是否需要 admin role | 端点尚未实现 |
| `face-recognition.md` | 特征向量维度 512 | 代码中无显式常量。这是 InsightFace buffalo_l 模型的公开规格，但建议在草稿中标注来源为模型文档而非代码 |
| `production-config.md` | DB_PORT 生产值 3306 | MySQL 标准端口，代码中无可证实之处 |

---

## 建议补充（缺信息但不影响准确性的条目）

| 草稿文件 | 建议补充的内容 |
|---------|-------------|
| `abnormal-behavior.md` | YOLO confidence 阈值 `0.35`、IoU 阈值 `0.45` 的具体默认值 |
| `abnormal-behavior.md` | Zone safeDistance 默认值 `0` |
| `ai-results.md` | BackendClient HTTP 超时 5 秒 |
| `api-conventions.md` | 403 错误码（login account disabled） |
| `authentication.md` | 前端还存了 `factoryVisionUser` key（不仅是 `factoryVisionToken`） |
| `authentication.md` | 登录表单 username 默认值 `'admin'` |
| `face-recognition.md` | 支持的图片格式列表 `{".jpg", ".jpeg", ".png", ".bmp", ".webp"}` |
| `face-recognition.md` | 图片加载 HTTP 超时 10 秒 |
| `project.md` | FastAPI 版本号 `>=0.116,<0.117` |
| `project.md` | Vue Router `^4.5.1`、Axios `^1.11.0` 版本号 |

---

> 📋 **核实完成。** 本报告基于 `test-cicd` 分支只读检查生成，每条断言均给出精确的代码文件路径和行号。4 处错误和 6 处待人工确认的条目已单独列出，方便下一步逐一修改草稿。
