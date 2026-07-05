[TOC]

# MFlux Studio — 数据库设计

## 1. 概述

使用 SQLite 作为存储引擎，通过 SQLAlchemy 2.0 ORM 进行访问。数据库文件位于 `backend/data/mflux.db`。

## 2. ER 图

```
+------------------+       +------------------+
|   ImageRecord    |       |  TaskRecord      |
|------------------|       |------------------|
| id (PK)          |       | id (PK)          |
| prompt           |       | task_id (UQ)     |
| negative_prompt  |       | type             |
| seed             |       | status           |
| model            |       | progress         |
| width            |       | total_steps      |
| height           |       | current_step     |
| steps            |       | elapsed          |
| guidance         |       | prompt           |
| strength         |       | params (JSON)    |
| image_path       |       | result_path      |
| thumbnail_path   |       | error            |
| generation_time  |       | create_time      |
| favorite         |       +------------------+
| batch_total      |
| batch_index      |       +------------------+
| task_id          |       | PromptTemplate   |
| create_time      |       |------------------|
+------------------+       | id (PK)          |
                           | title            |
+------------------+       | content          |
| ModelRecord      |       | category         |
|------------------|       | favorite         |
| id (PK)          |       | create_time      |
| name             |       +------------------+
| path             |
| model_type       |       +------------------+
| quantization     |       | Setting          |
| size_bytes       |       |------------------|
| is_default       |       | key (PK)         |
| last_used        |       | value            |
| create_time      |       +------------------+
+------------------+
```

## 3. 表结构

### 3.1 images — 图像记录

记录每次生成的图像元数据。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| prompt | TEXT | NOT NULL | 生成提示词 |
| negative_prompt | TEXT | DEFAULT '' | 反向提示词 |
| seed | BIGINT | NOT NULL | 随机种子 |
| model | VARCHAR(255) | NOT NULL | 使用的模型名称或路径 |
| width | INTEGER | DEFAULT 1024 | 图像宽度 |
| height | INTEGER | DEFAULT 1024 | 图像高度 |
| steps | INTEGER | DEFAULT 4 | 采样步数 |
| guidance | FLOAT | DEFAULT 3.5 | CFG 引导尺度 |
| strength | FLOAT | DEFAULT 0.8, NULLABLE | 图生图强度（仅 img2img 有效） |
| image_path | VARCHAR(512) | NOT NULL | 图像 URL 路径（如 `/api/output/xxx.png`） |
| thumbnail_path | VARCHAR(512) | DEFAULT '' | 缩略图路径（当前未使用） |
| generation_time | FLOAT | DEFAULT 0.0 | 生成耗时（秒） |
| favorite | BOOLEAN | DEFAULT FALSE | 收藏标记 |
| batch_total | INTEGER | DEFAULT 1 | 批次总数 |
| batch_index | INTEGER | DEFAULT 0 | 当前图片在批次中的序号 |
| task_id | VARCHAR(64) | DEFAULT '' | 关联的任务 ID |
| create_time | DATETIME | DEFAULT now() | 创建时间 |

**索引建议：**
- `create_time DESC` — 历史列表排序
- `(prompt, create_time)` — 搜索条件加速
- `favorite` — 收藏筛选
- `task_id` — 按任务溯源查询

### 3.2 prompts — 提示词模板

用户保存的可复用提示词模板。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| title | VARCHAR(255) | NOT NULL | 模板标题 |
| content | TEXT | NOT NULL | 提示词内容 |
| category | VARCHAR(64) | DEFAULT 'custom' | 分类：realistic/anime/landscape/portrait/custom |
| favorite | BOOLEAN | DEFAULT FALSE | 收藏标记 |
| create_time | DATETIME | DEFAULT now() | 创建时间 |

**索引建议：**
- `category` — 分类筛选
- `create_time DESC` — 列表排序

### 3.3 tasks — 任务记录

图像生成任务的持久化记录，与内存 TaskQueue 中的任务状态同步。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| task_id | VARCHAR(64) | UNIQUE, NOT NULL | UUID 格式的唯一任务标识 |
| type | VARCHAR(32) | DEFAULT 'text2img' | 任务类型：text2img / img2img |
| status | VARCHAR(16) | DEFAULT 'waiting' | 状态：waiting/running/completed/failed/cancelled |
| progress | INTEGER | DEFAULT 0 | 进度百分比 0-100 |
| total_steps | INTEGER | DEFAULT 0 | 总步数 |
| current_step | INTEGER | DEFAULT 0 | 当前步数 |
| elapsed | FLOAT | DEFAULT 0.0 | 已用时间（秒） |
| prompt | TEXT | DEFAULT '' | 生成提示词（冗余，便于列表显示） |
| params | TEXT | DEFAULT '' | JSON 格式的完整参数快照 |
| result_path | VARCHAR(512) | DEFAULT '' | 结果图片 URL 路径 |
| error | TEXT | DEFAULT '' | 失败时的错误信息 |
| create_time | DATETIME | DEFAULT now() | 创建时间 |

**索引建议：**
- `task_id` (UNIQUE) — 按 ID 查询
- `create_time DESC` — 历史列表排序

### 3.4 settings — 键值设置

应用设置的键值对存储。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| key | VARCHAR(128) | PK | 设置键名 |
| value | TEXT | DEFAULT '' | 设置值 |

**已使用键名：**

| 键名 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| default_model | string | '' | 默认模型名称 |
| default_width | int | 1024 | 默认宽度 |
| default_height | int | 1024 | 默认高度 |
| default_steps | int | 4 | 默认步数 |
| default_cfg | float | 3.5 | 默认 CFG |
| output_dir | string | ./output | 输出目录 |
| history_count | int | 100 | 历史记录保留数量 |

### 3.5 models — 模型记录

本地缓存的 Flux 模型记录。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| name | VARCHAR(255) | NOT NULL | 模型显示名称 |
| path | VARCHAR(512) | NOT NULL | 模型路径（本地路径或 HuggingFace repo_id） |
| model_type | VARCHAR(64) | DEFAULT 'mflux' | 模型类型 |
| quantization | VARCHAR(32) | DEFAULT '' | 量化精度：INT4/INT8/FP16/FP32/BF16/GGUF |
| size_bytes | BIGINT | DEFAULT 0 | 模型文件总大小（字节） |
| is_default | BOOLEAN | DEFAULT FALSE | 是否为默认模型 |
| last_used | DATETIME | NULLABLE | 最后使用时间 |
| create_time | DATETIME | DEFAULT now() | 创建时间 |

**索引建议：**
- `is_default` — 快速查找默认模型
- `name` — 按名称查询

## 4. 命名规范

| 约定 | 规则 |
|------|------|
| 表名 | 全小写英文复数形式：`images`、`prompts`、`tasks`、`settings`、`models` |
| 主键 | 统一使用 `id` (INTEGER, PK, AUTOINCREMENT) |
| 时间字段 | 统一为 `create_time`，使用 `DATETIME(timezone=True)` + `server_default=func.now()` |
| 外键字段 | 使用 `_id` 后缀，如 `task_id` |
| 布尔字段 | 使用 `is_` 前缀（如 `is_default`），或直接使用 `favorite` |
| 大小字段 | 使用 `_bytes` 后缀（如 `size_bytes`） |
| 路径字段 | 使用 `_path` 后缀（如 `image_path`、`result_path`） |

## 5. 数据访问模式

### 5.1 会话管理

通过 `get_db()` 依赖注入函数管理 SQLAlchemy 会话生命周期。后端启动时调用 `init_db()` 自动建表。

### 5.2 关键查询模式

| 场景 | 实现 |
|------|------|
| 图片列表（分页+搜索） | `filter(prompt.ilike(...)).order_by(desc(create_time)).offset().limit()` |
| 收藏筛选 | `filter(favorite == True)` |
| 批量删除 | `filter(id.in_(ids))` |
| 默认模型 | `filter(is_default == True)` |
| 模型扫描全量替换 | `delete()` + 批量 insert |
| 设置 upsert | 先查后改，不存在则创建 |
| 任务同步 | `filter(task_id == id)` 精确匹配 |

## 6. 数据清理与维护

| 操作 | 时机 | 说明 |
|------|------|------|
| 图片物理删除 | `DELETE /api/images/{id}` 时 | 同时删除对应图片文件和缩略图文件 |
| 模型扫描清除 | `POST /api/models/scan` 时 | 先清空 models 表再重新扫描 |
| 日志轮转 | 自动（10MB/文件，保留5份） | 由 RotatingFileHandler 管理 |

## 7. 升级与迁移策略

当前使用 SQLAlchemy `create_all()` 自动建表，不支持自动迁移。对于后续变更：

- **轻量变更**：新增列可通过 `add_column` 手动执行
- **正式迁移**：项目依赖中已包含 `alembic==1.14.0`，建议初始化 Alembic
- **环境变量**：设置 `DATABASE_URL` 可切换至其他数据库（如 PostgreSQL）

## 8. 注意事项

- SQLite 不支持并发写入，当前单用户场景无影响；多用户场景需切换至 PostgreSQL
- `check_same_thread=False` 允许在 TaskQueue 后台线程中使用独立 Session
- `image_path` 存储的是 URL 路径（如 `/api/output/xxx.png`），而非文件系统绝对路径
- `params` 字段以 JSON 文本格式存储完整参数快照，可用于故障排查和任务重放

---

## 9. 已知设计缺陷与技术债

以下问题来自 Architecture Review，应在后续迭代中解决。

### 9.1 SQLite 未启用 WAL 模式

当前未设置 `PRAGMA journal_mode=WAL`。TaskQueue 后台线程与 FastAPI 异步处理器同时写入时，SQLite 默认序列化模式可能导致 `database is locked` 错误。`_update_task_status` 静默吞掉所有异常，失败不可见。

**建议：** `engine = create_engine(..., connect_args={"check_same_thread": False})` 后执行 `PRAGMA journal_mode=WAL`，并增加写操作的显式异常处理。

### 9.2 image_path 存储 URL 导致文件删除失效

`image_path` 存储 URL 格式路径（`/api/output/xxx.png`），但 `images.py` 的删除端点使用 `os.path.exists()` 和 `os.remove()` 直接操作此字符串，总是返回 False，静默不删除物理文件。

**建议：** 存储时保留文件系统绝对路径，或删除前标准化：
```python
real_path = os.path.join(OUTPUT_DIR, os.path.basename(record.image_path))
```

### 9.3 thumbnail_path 是死字段

`ImageRecord.thumbnail_path` 已定义但从未写入有意义的值（始终为空字符串）。`images.py` 的删除逻辑试图检查并删除此路径。

**建议：** 实现缩略图生成（推荐用于浏览器性能），或移除此列。

### 9.4 偏移分页的性能瓶颈

当前使用 `page` + `page_size` 偏移分页，最大 100 条。当图片库增长到数千条时，SQLite 需扫描并跳过所有前序行。

**建议：** 图片数超过 ~1000 后迁移至 cursor 分页。

### 9.5 无显式事务管理

当前多表操作未使用 SQLAlchemy 显式事务。`_save_record()` 和 `_update_task_status()` 各自独立 Session，事务边界不明确。

**建议：** 对涉及多表一致性的操作使用 `session.begin()` 上下文管理器。
