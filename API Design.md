[TOC]

# MFlux Studio — API 接口设计

## 1. 概述

后端 API 基于 FastAPI 构建，所有路由以 `/api` 为前缀。API 文档自动生成于 `http://localhost:8765/docs`。

### 1.1 基础约定

- **请求体格式**：`application/json`（upload 接口除外）
- **响应格式**：统一 JSON 对象
- **分页参数**：`page` (≥1)、`page_size` (1-100)
- **时间格式**：ISO 8601（UTC）
- **错误响应**：`{"detail": "error message"}`，HTTP 状态码 4xx/5xx

### 1.2 接口总览

| 分组 | 前缀 | 路由数 |
|------|------|--------|
| 图像生成 | `/api/generate` | 2 |
| 图片管理 | `/api/images` | 5 |
| 提示词管理 | `/api/prompts` | 5 |
| 模型管理 | `/api/models` | 4 |
| 任务管理 | `/api/tasks` | 6 |
| 设置管理 | `/api/settings` | 2 |
| 文件上传 | `/api/upload` | 1 |
| WebSocket | `/ws` | 1 |
| 静态文件 | `/api/output`, `/api/files` | 2 |

## 2. 图像生成 API

### 2.1 Text-to-Image

```
POST /api/generate/text2img
```

提交文本提示词，生成图像。任务异步执行，通过 task_id 查询状态。

**Request Body：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | 是 | - | 生成提示词，不能为空 |
| negative_prompt | string | 否 | "" | 反向提示词（FLUX.1 模型支持，FLUX.2 自动忽略） |
| model | string | 否 | "" | 模型名称或路径，空值使用默认模型 |
| steps | int | 否 | 4 | 采样步数，最小 2 |
| guidance | float | 否 | 3.5 | CFG 引导尺度（FLUX.2 固定为 1.0） |
| seed | int | 否 | null | 随机种子，null 则自动生成 |
| width | int | 否 | 1024 | 图像宽度（512-1536） |
| height | int | 否 | 1024 | 图像高度（512-1536） |
| batch_count | int | 否 | 1 | 批次数量（1-8），每张图 seed 递增 |

**Response 200：**

```json
{
  "task_id": "uuid-string",
  "seed": 42,
  "status": "queued"
}
```

**Error 400：**
```json
{"detail": "Prompt is required"}
```

### 2.2 Image-to-Image

```
POST /api/generate/img2img
```

以上传的图片为底图，根据提示词生成变体。

**Request Body：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | 是 | - | 描述要生成的变化 |
| image_path | string | 是 | - | 上传图片的本地路径 |
| negative_prompt | string | 否 | "" | 反向提示词 |
| model | string | 否 | "" | 模型名称 |
| steps | int | 否 | 4 | 采样步数 |
| guidance | float | 否 | 3.5 | CFG 尺度 |
| seed | int | 否 | null | 随机种子 |
| strength | float | 否 | 0.8 | 对原图的保留强度（0.1-1.0） |

**Response 200：** 同 text2img

## 3. 图片管理 API

### 3.1 图片列表

```
GET /api/images?page=1&page_size=20&search=cat&favorite=true
```

**Query Parameters：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码，从 1 开始 |
| page_size | int | 否 | 20 | 每页数量，最大 100 |
| search | string | 否 | null | 提示词模糊搜索 |
| favorite | bool | 否 | null | 收藏筛选 |

**Response 200：** `ImageRecord[]`

```json
[
  {
    "id": 1,
    "prompt": "a beautiful cat",
    "negative_prompt": "",
    "seed": 42,
    "model": "mlx-community/flux2-klein-4b-4bit",
    "width": 1024,
    "height": 1024,
    "steps": 4,
    "guidance": 3.5,
    "image_path": "/api/output/xxx.png",
    "thumbnail_path": "",
    "generation_time": 5.2,
    "favorite": false,
    "batch_total": 1,
    "batch_index": 0,
    "create_time": "2026-07-05T10:00:00Z"
  }
]
```

### 3.2 单张图片详情

```
GET /api/images/{image_id}
```

**Response 200：** `ImageRecord`

### 3.3 更新图片（收藏）

```
PATCH /api/images/{image_id}
Content-Type: application/json

{"favorite": true}
```

**Request Body：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| favorite | bool | 否 | 收藏状态切换 |

**Response 200：** `{"status": "ok"}`

### 3.4 删除单张图片

```
DELETE /api/images/{image_id}
```

同时删除数据库记录和物理文件（图片+缩略图）。

**Response 200：** `{"status": "ok"}`

### 3.5 批量删除图片

```
DELETE /api/images
Content-Type: application/json

[1, 2, 3]
```

**Request Body：** `int[]` — 图片 ID 列表

**Response 200：** `{"status": "ok", "deleted": 3}`

## 4. 提示词管理 API

### 4.1 提示词列表

```
GET /api/prompts?category=realistic&favorite=true
```

**Query Parameters：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| category | string | 否 | "" | 分类筛选：realistic/anime/landscape/portrait/custom |
| favorite | bool | 否 | null | 收藏筛选 |

**Response 200：** `PromptTemplate[]`

```json
[
  {
    "id": 1,
    "title": "Cat Portrait",
    "content": "a detailed cat portrait, soft lighting",
    "category": "realistic",
    "favorite": false,
    "create_time": "2026-07-05T10:00:00Z"
  }
]
```

### 4.2 创建提示词

```
POST /api/prompts
Content-Type: application/json

{
  "title": "New Prompt",
  "content": "prompt content here",
  "category": "custom",
  "favorite": false
}
```

**Request Body：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| title | string | 是 | - | 标题，不能为空 |
| content | string | 是 | - | 内容，不能为空 |
| category | string | 否 | "custom" | 分类标签 |
| favorite | bool | 否 | false | 收藏 |

### 4.3 更新提示词

```
PUT /api/prompts/{prompt_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "favorite": true
}
```

所有字段可选，仅更新提供的字段。

### 4.4 删除提示词

```
DELETE /api/prompts/{prompt_id}
```

### 4.5 提示词增强

```
POST /api/prompts/enhance
Content-Type: application/json

{
  "prompt": "a cat",
  "style": "realistic",
  "language": "en"
}
```

**Request Body：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | 是 | - | 原始提示词 |
| style | string | 否 | "enhance" | 风格：enhance/realistic/anime/cinematic |
| language | string | 否 | "en" | 语言：en/zh |

**Response 200：**

```json
{
  "original": "a cat",
  "enhanced": "photorealistic, ultra detailed, 8K, realistic lighting, a cat, high quality, detailed, sharp focus"
}
```

**增强规则：**
- `enhance`：添加 `masterpiece, best quality, highly detailed` 前缀
- `realistic`：添加 `photorealistic, ultra detailed, 8K, realistic lighting` 前缀
- `anime`：添加 `anime style, cel shaded, vibrant colors` 前缀
- `cinematic`：添加 `cinematic lighting, dramatic composition, film grain` 前缀
- 中文提示词 (language=zh)：保留中文并添加 `masterpiece, best quality` 前缀
- 所有结果附加 `, high quality, detailed, sharp focus` 后缀

## 5. 模型管理 API

### 5.1 模型列表

```
GET /api/models
```

**Response 200：** `ModelRecord[]`

```json
[
  {
    "id": 1,
    "name": "flux2-klein-4b-4bit",
    "path": "mlx-community/flux2-klein-4b-4bit",
    "model_type": "mflux",
    "quantization": "INT4",
    "size_bytes": 2147483648,
    "is_default": true,
    "create_time": "2026-07-05T10:00:00Z"
  }
]
```

### 5.2 扫描本地模型

```
POST /api/models/scan
```

扫描 HuggingFace 缓存目录 (`~/.cache/huggingface/hub`) 和本地模型目录 (`~/Models`, `~/Downloads/models`)，清空并重建 models 表。

**Response 200：** `{"scanned": 5, "added": 5}`

### 5.3 删除模型记录

```
DELETE /api/models/{model_id}
```

仅删除数据库记录，不删除物理文件。

### 5.4 设置默认模型

```
POST /api/models/{model_id}/default
```

将所有模型的 `is_default` 设为 false，再将指定模型设为 true。

**Response 200：** `{"status": "ok", "model": "flux2-klein-4b-4bit"}`

## 6. 任务管理 API

### 6.1 任务历史

```
GET /api/tasks
```

返回最近 50 条任务记录。

### 6.2 当前队列

```
GET /api/tasks/queue
```

返回内存中的任务队列状态。

**Response 200：** `TaskInfo[]`

```json
[
  {
    "task_id": "uuid",
    "type": "text2img",
    "status": "running",
    "progress": 75,
    "total_steps": 4,
    "current_step": 3,
    "elapsed": 3.2,
    "prompt": "a beautiful cat",
    "queued_at": 1749000000.0,
    "started_at": 1749000001.0
  }
]
```

### 6.3 任务详情

```
GET /api/tasks/{task_id}
```

### 6.4 取消任务

```
POST /api/tasks/{task_id}/cancel
```

仅标记为 cancelled，无法真正停止正在运行的子进程。

### 6.5 取消所有任务

```
POST /api/tasks/cancel-all
```

### 6.6 重试任务

```
POST /api/tasks/{task_id}/retry
```

对已完成的 `completed/failed/cancelled` 任务创建新的队列条目。

## 7. 设置 API

### 7.1 获取所有设置

```
GET /api/settings
```

**Response 200：** `{"key1": "value1", "key2": "value2"}`

### 7.2 更新/创建设置

```
POST /api/settings
Content-Type: application/json

{
  "key": "default_steps",
  "value": "8"
}
```

upsert 语义：存在则更新，不存在则创建。

## 8. 文件上传 API

### 8.1 上传图片

```
POST /api/upload
Content-Type: multipart/form-data

file: @image.png
```

**支持的格式：** `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`

**Response 200：**

```json
{
  "filename": "uuid.png",
  "path": "./uploads/uuid.png",
  "url": "/api/files/uuid.png"
}
```

## 9. WebSocket API

### 9.1 连接

```
WebSocket /ws
```

### 9.2 客户端消息

| 类型 | 载荷 | 说明 |
|------|------|------|
| `ping` | `{"type": "ping"}` | 心跳检测 |

### 9.3 服务端推送

| 类型 | 载荷 | 触发时机 |
|------|------|----------|
| `pong` | `{"type": "pong"}` | 收到 ping 后回复 |
| `progress` | `{"type":"progress","task_id":"...","message":"...","current_step":3,"total_steps":4,"elapsed":3.2,"percent":75}` | 生成步数更新 |
| `task_error` | `{"type":"task_error","task_id":"...","error":"..."}` | 任务执行失败 |
| `task_completed` | `{"type":"task_completed","task_id":"...","result_path":"/api/output/xxx.png"}` | 任务执行成功 |

## 10. 静态文件挂载

| 路径 | 本地目录 | 用途 |
|------|----------|------|
| `/api/output` | `backend/output/` | 生成的图片文件 |
| `/api/files` | `backend/uploads/` | 用户上传的图片文件 |

## 11. 错误码汇总

| 状态码 | 含义 | 常见场景 |
|--------|------|----------|
| 200 | 成功 | |
| 400 | 请求参数错误 | 空 prompt、不支持的图片格式 |
| 404 | 资源不存在 | 图片/提示词/模型/任务未找到 |
| 500 | 服务端错误 | mflux CLI 未安装、磁盘空间不足 |

## 12. 前端代理配置

开发环境下，Vite 将 `/api` 和 `/ws` 代理到后端 `:8765`：

```javascript
// vite.config.js
server: {
  proxy: {
    '/api': { target: 'http://localhost:8765', changeOrigin: true },
    '/ws': { target: 'ws://localhost:8765', ws: true },
  },
}
```

生产构建时需配置 Nginx 或等效反向代理。
