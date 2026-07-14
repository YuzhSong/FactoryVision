# OpenSpec 使用说明

本文说明组内成员如何在本项目中使用 OpenSpec 进行规范驱动开发。

## 1. OpenSpec 是什么

OpenSpec 是一种“先写清需求，再写代码”的开发流程。

它的作用是：

- 在编码前明确功能要求。
- 记录需求变更原因和影响范围。
- 给 AI 编码助手提供清晰上下文。
- 让实现结果可以对照规范验收。
- 避免只靠口头沟通导致接口、前端、后端理解不一致。

简单理解：

```text
OpenSpec = 功能需求说明 + 变更记录 + 验收标准
```

## 2. 是否需要安装 CLI

如果只是阅读规范，不需要安装 CLI。

如果要创建、校验、归档 OpenSpec 变更，建议安装 CLI。

安装要求：

```text
Node.js >= 20.19.0
```

安装命令：

```powershell
npm install -g @fission-ai/openspec@latest
```

验证安装：

```powershell
openspec --version
```

在项目根目录检查：

```powershell
cd E:\小学期\FactoryVision
openspec list
openspec validate --all --no-interactive
```

如果看到 specs 校验通过，说明本地环境可用。

## 3. 本项目 OpenSpec 目录

当前项目使用 CLI 认可的结构：

```text
openspec/
├── project.md
├── specs/
│   ├── authentication/
│   │   └── spec.md
│   ├── employee-management/
│   │   └── spec.md
│   └── ...
├── changes/
└── audit/
```

说明：

- `project.md`：项目整体背景、技术栈、开发原则。
- `specs/`：已经确认的正式规范。
- `changes/`：正在进行或准备进行的需求变更。
- `audit/`：规范与代码对账记录，作为参考材料。

## 4. 什么时候需要使用 OpenSpec

建议使用 OpenSpec 的情况：

- 新增功能。
- 修改业务流程。
- 修改接口参数或返回值。
- 修改数据库结构。
- 修改认证、权限、安全规则。
- 修改 AI 服务输入输出。
- planned 功能变为 implemented。

一般不需要使用 OpenSpec 的情况：

- 只改样式。
- 改文案。
- 修一个不影响行为的小 bug。
- 代码重构但功能表现不变。

## 5. 标准开发流程

### 第一步：创建变更

在 `openspec/changes/` 下创建一个变更目录：

```text
openspec/changes/<change-name>/
```

建议命名：

```text
add-face-enroll-three-views
update-employee-search
add-alert-handle-flow
```

目录中通常包含：

```text
proposal.md
tasks.md
specs/<affected-spec>/spec.md
```

### 第二步：写 proposal.md

说明为什么要改、改什么、影响哪些模块。

示例：

```md
# Change: Add employee search filters

## Why

员工数量增加后，需要按姓名、部门和状态快速筛选。

## What Changes

- 员工列表支持关键词搜索。
- 员工列表支持部门和状态筛选。
- 前端筛选栏调用后端列表接口。

## Affected Specs

- employee-management
- api-conventions
```

### 第三步：写 tasks.md

拆成可执行任务。

示例：

```md
# Tasks

- [ ] 更新 employee-management spec
- [ ] 调整后端员工列表参数
- [ ] 更新 Swagger 注解
- [ ] 前端 EmployeesView 接入员工列表接口
- [ ] 运行后端检查和前端构建
```

### 第四步：写 spec delta

在变更目录中写规范差异。

示例路径：

```text
openspec/changes/add-employee-search/specs/employee-management/spec.md
```

示例内容：

```md
## ADDED Requirements

### Requirement: Search employees

The system SHALL allow authenticated users to search employees by keyword, department, and status.

#### Scenario: Search employees by keyword

- **GIVEN** the user is authenticated
- **WHEN** `GET /api/employees/list/?keyword=张&page=1&pageSize=20` is called
- **THEN** the response SHALL return employees whose name or employee number matches the keyword
```

### 第五步：校验变更

```powershell
openspec validate <change-name>
```

如果不确定，也可以全量校验：

```powershell
openspec validate --all --no-interactive
```

### 第六步：实现代码

确认规范后，再修改代码。

代码完成后，根据具体模块运行检查，例如：

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py check
```

```powershell
cd frontend
npm run build
```

### 第七步：归档变更

功能完成并确认后，归档变更：

```powershell
openspec archive <change-name> --yes
```

归档会把变更合并进正式 `openspec/specs/`，并记录变更历史。

## 6. 常用命令

查看当前变更：

```powershell
openspec list
```

查看某个变更：

```powershell
openspec show <change-name>
```

校验某个变更：

```powershell
openspec validate <change-name>
```

校验所有规范：

```powershell
openspec validate --all --no-interactive
```

归档变更：

```powershell
openspec archive <change-name> --yes
```

## 7. 给 AI 助手的提示词格式

### 只创建 OpenSpec，不写代码

```text
请按 OpenSpec 流程为【功能名称】创建变更提案。

要求：
- 先阅读 openspec/project.md 和相关 specs
- 在 openspec/changes 下创建 change
- 编写 proposal.md、tasks.md 和 spec delta
- 运行 openspec validate <change-name>
- 暂时不要修改业务代码，等我确认后再开发
```

### 创建 OpenSpec 并实现功能

```text
请按 OpenSpec 流程开发【功能名称】。

要求：
- 先创建 OpenSpec change
- 写清 Why、What Changes、Affected Specs、Acceptance
- 运行 openspec validate
- 再按 tasks 实现代码
- 完成后运行相关检查和构建
- 最后说明修改了哪些文件、验证结果是什么
```

### 修改已有功能

```text
请按 OpenSpec 流程修改【已有功能】。

变更内容：
- 【写清楚要改什么】

要求：
- 先检查现有 openspec/specs 是否覆盖该功能
- 如果现有 spec 过时，先创建 change 更新规范
- 确认后再修改代码
- 不要引入无关功能
```

### 只判断是否需要 OpenSpec

```text
请判断这个需求是否需要走 OpenSpec 流程：

【粘贴需求】

如果需要，请说明影响哪些 specs。
如果不需要，请说明原因。
先不要改代码。
```

## 8. 推荐协作规则

团队协作时建议遵守：

- 影响接口、数据结构、业务流程的需求必须走 OpenSpec。
- 小样式、小文案、小 bug 可以不走 OpenSpec。
- 后端新增接口时，同时更新 Swagger 和 OpenSpec。
- AI 服务新增结果类型时，同时更新 AI 相关 spec 和 API spec。
- 前端流程变化时，同步更新对应页面或业务 spec。
- 提交代码前运行 `openspec validate --all --no-interactive`。

## 9. 一句话总结

```text
OpenSpec 用来先统一需求，再指导代码实现；Swagger 用来说明后端接口怎么调用。
```

实际开发中：

```text
OpenSpec 定需求
Swagger 对接口
代码做实现
测试做验证
```
