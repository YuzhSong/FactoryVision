# Swagger 接口管理使用说明

本文说明本项目如何使用 Swagger，以及前后端开发时应该怎么配合使用。

## 1. Swagger 在项目里的作用

Swagger 不是业务功能页面，而是开发阶段使用的接口管理工具，主要作用有：

- **查看接口**：知道后端有哪些接口、路径是什么、请求方式是什么。
- **确认参数**：查看每个接口需要传哪些字段、字段类型和是否必填。
- **查看返回值**：了解接口成功或失败时返回什么数据。
- **在线测试**：通过 Swagger UI 直接调用接口，验证接口是否可用。
- **生成文档**：导出 `openapi.yaml` / `openapi.json`，作为结题接口文档。

## 2. 本项目 Swagger 地址

启动后端后访问：

```text
http://127.0.0.1:8000/api/docs/
```

OpenAPI schema 地址：

```text
http://127.0.0.1:8000/api/schema/
```

已生成的接口文档文件：

```text
docs/api/openapi.yaml
docs/api/openapi.json
```

## 3. 后端同学如何使用

新增或修改接口时，建议按以下流程：

1. 编写接口逻辑。
2. 编写或更新 serializer。
3. 在 `urls.py` 注册接口路径。
4. 在 view 上补充 `@extend_schema` 注解。
5. 打开 Swagger 页面，确认接口展示正确。
6. 使用 `Try it out` 测试接口。
7. 重新生成 OpenAPI 文档。

示例：

```python
@extend_schema(
    summary="创建员工",
    description="新增员工档案。工号重复时返回 409。",
    request=EmployeeCreateSerializer,
    responses={200: None, 400: None, 409: None},
)
@api_view(["POST"])
def employee_root_view(request):
    ...
```

注意：如果接口参数、返回结构、认证要求发生变化，也要同步更新 `@extend_schema`，否则 Swagger 文档会和真实接口不一致。

## 4. 前端同学如何使用

前端开发页面前，先看 Swagger：

1. 找到需要调用的接口。
2. 查看接口路径、请求方式和参数。
3. 先用 Swagger 的 `Try it out` 测试接口是否可用。
4. 再到 `frontend/src/api/modules.js` 中封装请求。
5. 页面中调用封装好的 API。

如果前端页面调用失败，可以先在 Swagger 里测试同一个接口：

- Swagger 能调通，前端调不通：优先检查前端请求参数、token、baseURL。
- Swagger 也调不通：优先检查后端接口逻辑或权限配置。

## 5. 如何测试需要登录的接口

有些接口需要登录认证，例如：

```python
@permission_classes([IsAuthenticated])
```

这类接口需要带 JWT token。

操作步骤：

1. 在 Swagger 中调用登录接口：

```text
POST /api/auth/login/
```

2. 输入用户名和密码，点击 `Execute`。
3. 从响应中复制 `data.token`。
4. 点击 Swagger 页面右上角 `Authorize`。
5. 输入：

```text
Bearer 复制的token
```

注意 `Bearer` 和 token 中间有一个空格。

6. 再测试需要登录的接口。

## 6. 如何生成提交用接口文档

在后端目录执行：

```powershell
cd E:\小学期\FactoryVision\backend
.\.venv\Scripts\python.exe manage.py spectacular --file ..\docs\api\openapi.yaml --validate
.\.venv\Scripts\python.exe manage.py spectacular --file ..\docs\api\openapi.json --format openapi-json --validate
```

生成后提交：

```text
docs/api/openapi.yaml
docs/api/openapi.json
```

通常优先提交 `openapi.yaml`，它是标准 Swagger/OpenAPI 接口文档。

## 7. 常见问题

### Swagger 会影响程序运行吗？

一般不会。Swagger 主要影响接口文档展示和在线测试，不改变业务逻辑。

### Swagger 会阻止后端修改接口吗？

不会。后端可以正常修改接口，但修改后要同步更新 Swagger 注解和生成文档。

### 点 Execute 会影响数据吗？

会。`Execute` 会真实调用后端接口：

- `GET` 查询接口一般只读取数据。
- `POST` / `PUT` / `DELETE` 可能会新增、修改或删除数据。

测试写入类接口前要确认使用的是测试数据。

## 8. 结题支撑材料建议

为了证明项目真实使用 Swagger，建议准备：

- Swagger UI 页面截图。
- 登录接口测试截图。
- 一个需要 token 的接口测试截图。
- `docs/api/openapi.yaml`。
- `docs/api/openapi.json`。
- 后端 `@extend_schema` 注解代码截图。

一句话总结：

> Swagger 是本项目的接口说明书、在线测试工具和结题接口文档来源。每次新增或修改接口，都应同步更新 Swagger 注解并重新生成 OpenAPI 文档。
