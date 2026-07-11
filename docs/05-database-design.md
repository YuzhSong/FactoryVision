# 数据库设计

## 当前状态

已实现 7 张业务表。开发阶段使用 SQLite，目标部署为 MySQL。`attendance_record` 表为 `planned`。

## ER 图

```mermaid
erDiagram
    user ||--o{ "" : manages
    employee ||--o{ face_feature : owns
    camera ||--o{ zone : contains
    camera ||--o{ event : records
    event ||--o| alert : triggers
    zone ||--o{ event : related_to
```

## 表关系

1. `employee` 与 `face_feature` 为一对多关系，一个员工可录入多个人脸特征。
2. `camera` 与 `zone` 为一对多关系，一个摄像头可配置多个警戒区域。
3. `camera` 与 `event` 为一对多关系，一个摄像头可产生多条事件。
4. `event` 与 `alert` 为一对一关系，一个事件可能触发一个告警。
5. `zone` 与 `event` 为一对多关系（通过 zone_id 间接关联）。

## user

基于 Django `auth_user` 扩展。

| 字段名 | 类型 | 是否为空 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 否 | 用户 ID |
| `username` | varchar(150) | 否 | 登录账号 |
| `password` | varchar(128) | 否 | 加密密码 |
| `role` | varchar(32) | 否 | admin / operator |
| `is_active` | boolean | 否 | 是否启用 |
| `last_login` | datetime | 是 | 最近登录时间 |
| `created_at` | datetime | 否 | 创建时间 |
| `updated_at` | datetime | 否 | 更新时间 |

## employee

| 字段名 | 类型 | 是否为空 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 否 | 员工 ID |
| `employee_no` | varchar(64) | 否 | 工号，唯一 |
| `name` | varchar(64) | 否 | 姓名 |
| `department` | varchar(128) | 是 | 部门 |
| `position` | varchar(128) | 是 | 岗位 |
| `phone` | varchar(32) | 是 | 手机号 |
| `status` | varchar(32) | 否 | active / inactive |
| `created_at` | datetime | 否 | 创建时间 |
| `updated_at` | datetime | 否 | 更新时间 |

## face_feature

| 字段名 | 类型 | 是否为空 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 否 | 人脸特征 ID |
| `employee_id` | bigint | 否 | 关联员工 ID |
| `feature_vector` | json | 否 | 512 维人脸特征向量 |
| `image_path` | varchar(255) | 是 | 原始人脸图片路径 |
| `face_type` | varchar(32) | 是 | front / left / right |
| `created_at` | datetime | 否 | 创建时间 |

## camera

| 字段名 | 类型 | 是否为空 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 否 | 摄像头 ID |
| `name` | varchar(128) | 否 | 摄像头名称 |
| `code` | varchar(64) | 否 | 唯一编码，可自动生成 |
| `stream_url` | varchar(512) | 否 | 原始 RTMP 流地址，AI 拉流 |
| `processed_stream_url` | varchar(512) | 否 | AI 处理后带框流地址，前端播放 |
| `location` | varchar(255) | 否 | 安装位置 |
| `status` | varchar(32) | 否 | online / offline / disabled |
| `enabled` | boolean | 否 | 是否启用，默认 true |
| `created_at` | datetime | 否 | 创建时间 |
| `updated_at` | datetime | 否 | 更新时间 |

## zone

| 字段名 | 类型 | 是否为空 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 否 | 区域 ID |
| `camera_id` | bigint | 否 | 关联摄像头 ID (FK) |
| `name` | varchar(128) | 否 | 区域名称 |
| `type` | varchar(32) | 否 | restricted / danger / workstation / general |
| `points` | json | 否 | 多边形坐标 [{x,y}] |
| `enabled` | boolean | 否 | 是否启用 |
| `description` | text | 否 | 描述 |
| `created_at` | datetime | 否 | 创建时间 |
| `updated_at` | datetime | 否 | 更新时间 |

## event

| 字段名 | 类型 | 是否为空 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 否 | 事件 ID |
| `camera_id` | bigint | 是 | 关联摄像头 ID (FK) |
| `camera_identifier` | varchar(64) | 否 | 摄像头标识字符串 |
| `event_type` | varchar(64) | 否 | 事件类型 |
| `source` | varchar(32) | 否 | 来源，当前为 ai_service |
| `severity` | varchar(32) | 否 | info / low / medium / high |
| `status` | varchar(32) | 否 | new / processing / closed |
| `occurred_at` | datetime | 否 | 事件发生时间 |
| `frame_id` | varchar(128) | 否 | 视频帧 ID |
| `track_id` | varchar(128) | 否 | AI 跟踪 ID |
| `bbox` | json | 否 | 检测框坐标 |
| `confidence` | float | 是 | 置信度 |
| `snapshot_path` | varchar(512) | 否 | 截图路径 |
| `payload` | json | 否 | 原始 AI 结果 |
| `created_at` | datetime | 否 | 创建时间 |
| `updated_at` | datetime | 否 | 更新时间 |

## alert

与 `event` 一对一关系。不是所有事件都有告警，只有触发告警规则的事件才生成。

| 字段名 | 类型 | 是否为空 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 否 | 告警 ID |
| `event_id` | bigint | 否 | 关联事件 ID (OneToOne) |
| `camera_id` | bigint | 是 | 关联摄像头 ID (FK, 冗余) |
| `event_type` | varchar(64) | 否 | 事件类型（冗余） |
| `level` | varchar(32) | 否 | medium / high |
| `status` | varchar(32) | 否 | pending / processing / closed |
| `title` | varchar(128) | 否 | 告警标题 |
| `description` | text | 否 | 告警描述 |
| `snapshot_path` | varchar(512) | 否 | 截图路径（冗余） |
| `occurred_at` | datetime | 否 | 发生时间（冗余） |
| `created_at` | datetime | 否 | 创建时间 |

## 索引建议

| 表 | 索引 | 说明 |
| --- | --- | --- |
| `employee` | `employee_no` unique | 工号唯一查询 |
| `face_feature` | `employee_id` | 员工人脸特征查询 |
| `camera` | `code` unique | 编码唯一查询 |
| `camera` | `status` | 摄像头状态筛选 |
| `zone` | `camera_id` | 摄像头区域查询 |
| `event` | `camera_id, occurred_at` | 按摄像头和时间查询事件 |
| `event` | `event_type, severity` | 告警筛选 |
| `alert` | `event_id` unique | 事件关联查询 |
| `alert` | `status, occurred_at` | 告警状态和时间排序 |
