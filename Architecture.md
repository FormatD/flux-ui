[TOC]

# MFlux Studio — 系统架构设计

## 1. 概述

MFlux Studio 是一个本地优先的 AI 图像生成桌面应用，通过友好的 Web UI 调用 Flux 模型（MLX 加速）进行推理。

### 1.1 架构原则

- **本地优先**：所有模型推理在用户本机完成，不依赖云服务
- **单体部署**：前后端在同一主机上运行，通过 HTTP/WebSocket 通信
- **异步任务**：图像生成作为后台任务异步执行，前端通过 WebSocket 实时获取进度
- **无状态 API**：后端 API 设计为无状态，会话状态由前端 Pinia Store 管理
- **渐进式**：SQLite 作为默认存储，未来可扩展为更重量级的数据库

### 1.2 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 (Composition API) | SPA 应用 |
| 前端构建 | Vite 6 | 开发代理到后端 |
| UI 组件库 | Element Plus 2.9 | 表单、表格、对话框、菜单等 |
| 状态管理 | Pinia 2 + pinia-plugin-persistedstate | 持久化主题和侧边栏状态 |
| 路由 | Vue Router 4 | 7 个页面路由 |
| HTTP 客户端 | Axios | 后端 API 调用 |
| 后端框架 | FastAPI | RESTful API + WebSocket |
| ORM | SQLAlchemy 2.0 | 声明式 ORM，SQLite 驱动 |
| 数据库 | SQLite | 本地单文件数据库 |
| 图像生成引擎 | mflux CLI (MLX) | 调用本地 Flux 模型 |
| 实时通信 | WebSocket (FastAPI) | 任务进度推送 |
| 日志 | Python logging + RotatingFileHandler | 控制台和文件日志 |
| 测试 | Playwright (Firefox) + urllib | E2E 和 API 测试 |

## 2. 系统架构图

```
+-------------------+         HTTP/REST          +-------------------+
|                   | -------------------------> |                   |
|   Vue 3 SPA       |                            |   FastAPI 后端     |
|   (Port 5173)     | <------------------------- |   (Port 8765)     |
|                   |        JSON Response       |                   |
|   +-------------+ |                            |   +-------------+ |
|   | Pinia Store | |                            |   | Task Queue  | |
|   +-------------+ |                            |   +-------------+ |
|   +-------------+ |        WebSocket           |         |         |
|   | WebSocket   | | <========================> |   +-----v-----+ |
|   | Client      | |      实时进度推送           |   | mflux CLI  | |
|   +-------------+ |                            |   | (MLX)      | |
|                   |                            |   +-----------+ |
|   +-------------+ |                            |   +-------------+ |
|   | Axios       | |                            |   | SQLAlchemy  | |
|   +-------------+ |                            |   +------+------+ |
+-------------------+                            |          |        |
                                                  |   +------v------+ |
                                                  |   |  SQLite     | |
                                                  |   |  mflux.db   | |
                                                  |   +-------------+ |
                                                  +-------------------+
                                                           |
                                                  +--------v--------+
                                                  |  Output /       |
                                                  |  Uploads /      |
                                                  |  Logs /         |
                                                  |  (本地文件系统)   |
                                                  +-----------------+
```

## 3. 模块划分

### 3.1 后端模块

| 模块 | 目录 | 职责 |
|------|------|------|
| 应用入口 | `backend/app/main.py` | FastAPI 应用初始化、生命周期管理、中间件、WebSocket 端点、静态文件挂载 |
| 数据库层 | `backend/app/database.py` | SQLAlchemy 引擎、会话工厂、`get_db` 依赖注入 |
| ORM 模型 | `backend/app/models.py` | 5 个实体模型定义 |
| 日志系统 | `backend/app/logger.py` | 滚动文件日志 + 控制台日志，单例 Logger |
| WebSocket 管理器 | `backend/app/websocket_manager.py` | 连接注册/注销、广播、进度回调 |
| 路由 - 图像生成 | `backend/app/routers/generate.py` | text2img / img2img 生成请求入口 |
| 路由 - 图片管理 | `backend/app/routers/images.py` | 图片 CRUD、批量删除、收藏 |
| 路由 - 提示词管理 | `backend/app/routers/prompts.py` | 提示词模板 CRUD、提示词增强 |
| 路由 - 模型管理 | `backend/app/routers/models.py` | 模型列表、扫描、设置默认 |
| 路由 - 任务 | `backend/app/routers/tasks.py` | 任务查询、取消、重试、取消全部 |
| 路由 - 设置 | `backend/app/routers/settings.py` | 键值对设置读写 |
| 路由 - 上传 | `backend/app/routers/upload.py` | 图片上传、文件服务 |
| Schema 定义 | `backend/app/schemas/schemas.py` | Pydantic 请求/响应模型 |
| 生成服务 | `backend/app/services/generator.py` | mflux CLI 调用、磁盘检查、模型解析、图像保存 |
| 任务队列 | `backend/app/services/task_queue.py` | 线程安全 FIFO 队列、异步处理循环 |
| 模型扫描 | `backend/app/services/model_scanner.py` | HuggingFace 缓存扫描、本地目录扫描 |

### 3.2 前端模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 应用入口 | `frontend/src/main.js` | Vue 应用创建、Pinia/Router/ElementPlus 注册 |
| 根组件 | `frontend/src/App.vue` | 侧边栏布局、路由视图、TaskPanel 浮动面板 |
| 路由定义 | `frontend/src/router/index.js` | 7 条路由配置，懒加载视图 |
| Pinia Store | `frontend/src/stores/app.js` | 全局状态：主题、侧边栏、WebSocket、任务列表 |
| HTTP 客户端 | `frontend/src/api/index.js` | Axios 实例，统一错误处理 |
| 全局样式 | `frontend/src/styles/index.css` | CSS 变量体系、主题切换、滚动条 |
| Text-to-Image 页 | `frontend/src/views/Text2Img.vue` | 提示词输入、参数面板、预览、Prompt 增强弹窗 |
| Image-to-Image 页 | `frontend/src/views/Img2Img.vue` | 图片拖拽上传、强度滑块、生成 |
| History 页 | `frontend/src/views/History.vue` | 图片网格、搜索、收藏、预览弹窗、下载 |
| Browser 页 | `frontend/src/views/Browser.vue` | Grid/Masonry 切换、多选、批量删除 |
| Prompt 管理页 | `frontend/src/views/Prompts.vue` | 分类标签、卡片列表、CRUD 弹窗 |
| 模型管理页 | `frontend/src/views/Models.vue` | 表格展示、模型扫描、设置默认 |
| 设置页 | `frontend/src/views/Settings.vue` | 生成默认值、主题、存储设置 |
| 图片预览组件 | `frontend/src/components/ImagePreview.vue` | 图片预览容器，支持加载态和占位 |
| 参数面板组件 | `frontend/src/components/ParameterPanel.vue` | 生成参数表单：尺寸、步数、CFG、种子、模型选择 |
| 任务面板组件 | `frontend/src/components/TaskPanel.vue` | 浮动任务列表，实时进度，取消操作 |

## 4. 关键设计决策

### 4.1 为什么使用 WebSocket 而非轮询

- **实时性**：WebSocket 推送使任务进度延迟 < 100ms
- **效率**：避免前端每隔 1-2 秒发起 HTTP 轮询
- **双向通信**：前端可发送 ping/pong 维持连接
- **降级方案**：Text2Img/Img2Img 视图仍保留 HTTP 轮询作为备选

### 4.2 为什么使用子进程调用 mflux CLI

- **隔离性**：mflux CLI 可能存在内存泄漏或崩溃，子进程不会影响后端进程
- **兼容性**：直接复用 pip 安装的 mflux 命令行，无需引入 Python SDK 绑定
- **简化**：避免在 Python 进程内加载 MLX/PyTorch 模型导致内存膨胀

### 4.3 为什么使用内存任务队列而非消息队列

- **本地场景**：单用户使用，不存在分布式协调需求
- **简单性**：Python `threading` + `deque` 即可满足 FIFO 顺序执行
- **无需持久化**：任务失败或重启后不要求恢复队列

### 4.4 为什么使用 CSS 变量实现主题

- **零运行时开销**：纯 CSS 方案，无需 JavaScript 主题切换逻辑
- **Element Plus 兼容**：通过 `html.dark` 类名与 Element Plus 暗色模式对齐
- **Pinia 持久化**：通过 `pinia-plugin-persistedstate` 保存主题偏好到 localStorage

## 5. 数据流

### 5.1 图像生成流程

```
用户点击 Generate
       |
       v
前端 POST /api/generate/text2img
       |
       v
后端 generate.py → task_queue.add_task()
       |
       v (返回 task_id)
任务入队，状态: waiting
       |
       v (后台线程 _process_loop)
任务状态更新为: running
       |
       v
调用 generator.generate_image()
       |
       v
子进程执行 mflux-generate CLI
       |
       +---> WebSocket 推送 progress 事件
       |         |
       |         v
       |     前端更新 TaskPanel 进度条
       |
       v
子进程完成 → 保存图片到 output/ 目录
       |
       v
保存 ImageRecord 到数据库
       |
       v
更新 TaskRecord 状态为: completed
       |
       v
WebSocket 推送 task_completed 事件
       |
       v
前端 Text2Img 轮询检测完成 → 加载图片显示
```

### 5.2 WebSocket 连接生命周期

```
前端 App.vue onMounted()
       |
       v
WebSocket 连接 → ws://localhost:5173/ws
       |
       v (Vite proxy)
ws://localhost:8765/ws
       |
       v
FastAPI 接受连接 → manager.connect(ws)
       |
       v
前端发送 {"type": "subscribe"}
       |
       v
后端事件循环推送:
  - progress    → 任务进度更新
  - task_error  → 任务失败
  - task_completed → 任务完成
       |
       v
前端断开/错误 → 3 秒后自动重连
```

## 6. 安全设计

| 方面 | 当前方案 | 说明 |
|------|----------|------|
| CORS | `allow_origins=["*"]` | 本地使用可行，网络暴露需收紧 |
| 认证 | 无 | 单用户本地应用，无认证需求 |
| 文件上传 | 格式白名单 `.png/.jpg/.jpeg/.webp/.bmp` | 防止任意文件上传 |
| 文件路径 | UUID 重命名上传文件 | 防止路径遍历 |
| 敏感配置 | `.env` 文件 | 不提交到版本控制 |
| 日志 | 不含敏感信息 | 仅记录操作摘要 |

## 7. 性能设计

| 场景 | 策略 |
|------|------|
| 图片列表查询 | 分页（默认 20 条/页）、搜索过滤、收藏筛选 |
| 模型扫描 | 单次扫描后缓存到数据库，不重复遍历文件系统 |
| 任务轮询 | 前端 polling 间隔 2s，与 WebSocket 并行使用 |
| 子进程管理 | 同一时间只运行一个生成任务（FIFO 队列） |
| 磁盘空间检查 | 生成前检查可用空间是否 < 100MB |
| 日志轮转 | 10MB 文件大小，保留 5 个备份 |

## 8. 扩展性考量

| 方向 | 方案 |
|------|------|
| 多用户支持 | 加入用户认证（OAuth2 + JWT），数据库添加 user_id 字段 |
| 分布式任务队列 | 替换内存 TaskQueue 为 Celery/Redis 后端 |
| 替代数据库 | 替换 DATABASE_URL 环境变量指向 PostgreSQL |
| GPU 集群 | 将 generator 抽离为独立 RPC 服务 |
| 图库浏览器 | 增加 EXIF/元数据标签，实现标签树 + 搜索 |
| 国际化 i18n | 已预留 language 设置字段，引入 vue-i18n |
