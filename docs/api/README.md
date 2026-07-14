# OpenAPI 导出文件

- `openapi.yaml` 与 `openapi.json` 由 Backend 的 `manage.py spectacular` 生成。
- 重新导出：

```powershell
backend\.venv\Scripts\python.exe backend\manage.py spectacular --file docs\api\openapi.yaml --format openapi
backend\.venv\Scripts\python.exe backend\manage.py spectacular --file docs\api\openapi.json --format openapi-json
```

当前生成器会对部分函数式视图报告“无法推断 serializer”，因此摄像头流控制、摄像头删除、人脸库和区域详情等接口可能未完整进入导出文件。运行时 Swagger 使用同一生成器；这些接口的人工说明保留在 `docs/04-api-design.md`。本次文档收尾不修改业务代码或 Swagger 注解。
