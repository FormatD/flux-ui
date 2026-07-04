# MFlux Studio - Bug Report

## 测试概况

- **测试框架**: Playwright (Firefox headless) + urllib API 测试
- **测试总数**: 49
- **通过**: 49
- **失败**: 0
- **发现的 Bug**: 3 (均已修复)

---

## Bug 1: FLUX.2 模型不支持 `--negative-prompt` 参数

### 现象

当生成图片时指定 `negative_prompt`（反向提示词），FLUX.2 系列模型（如 `flux2-klein-4b`）的 CLI 进程输出帮助信息后退出，任务标记为 `failed`。

请求参数：
```json
{
  "prompt": "detailed dragon",
  "negative_prompt": "blurry",
  "model": "mlx-community/flux2-klein-4b-4bit"
}
```

错误日志：
```
mflux-generate-flux2: error: --negative-prompt is not supported for FLUX.2. 
Focus on describing what you want.
```

### 原因

`mflux-generate-flux2` CLI 的 FLUX.2 模型不支持 `--negative-prompt` 参数。该标志仅用于 FLUX.1 模型（通过 `mflux-generate` CLI）。当 backend 的 `generator.py` 无条件添加 `--negative-prompt` 时，FLUX.2 CLI 报参数错误。

### 修复

**文件**: `backend/app/services/generator.py`

在添加 `--negative-prompt` 前检测模型类型：

```python
if negative_prompt:
    is_klein_cmd = "klein" in model.lower() or "flux2" in model.lower()
    if is_klein_cmd:
        log.warning("negative_prompt not supported for FLUX.2, skipping")
    else:
        cmd.extend(["--negative-prompt", negative_prompt])
```

FLUX.2 模型收到反向提示词时自动忽略并记录 warning。

---

## Bug 2: 图片 API 访问测试未正确处理二进制响应

### 现象

测试脚本中 `test_api_generation()` 的 `image accessible` 检查失败。生成的图片已成功保存到磁盘，但测试代码无法验证其 HTTP 可访问性。

### 原因

`api_get()` 函数使用 `urllib` 获取响应后，始终尝试 `json.loads(content)` 解析响应体。图片 URL（如 `/api/output/xxx.png`）返回的是 PNG 二进制数据：
- PNG 文件头以字节 `0x89` 开头，不是有效的 UTF-8 编码
- `json.loads()` 解码时先做 UTF-8 decode，抛出 `UnicodeDecodeError`（而非 `JSONDecodeError`）
- `except json.JSONDecodeError` 无法捕获 `UnicodeDecodeError`，异常向上抛出
- `except Exception` 捕获后返回 `(0, error_message)`

### 修复

**文件**: `tests/test_mflux.py`

扩大异常捕获范围，同时处理 `UnicodeDecodeError` 和 `ValueError`：

```python
except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
    return r.status, {"_bytes": len(content)}
```

对于非 JSON 的二进制响应（如图片），返回状态码和字节长度而非尝试 JSON 解析。

---

## Bug 3: `result_path` 存储本地文件路径而非 URL 路径（已在前序修复）

### 现象

History 和 Browser 页面中图片无法显示，`<img>` 标签的 `src` 指向 `./output/xxx.png`。

### 原因

`generator.py` 的 `_save_record()` 将图片的本地文件系统路径（如 `./output/xxx.png`）存入数据库的 `image_path` 字段。前端直接使用该路径作为 `<img :src>`，浏览器无法从 `./output/` 访问。

### 修复

**文件**: `backend/app/services/generator.py`

新增 `_url_path()` 函数将文件路径转换为 URL 路径：

```python
def _url_path(filepath: str) -> str:
    return f"/api/output/{os.path.basename(filepath)}"
```

保存记录时使用 URL 路径而非文件路径，前端通过 Vite proxy → FastAPI StaticFiles 获取图片。

---

## 测试用例清单

| 测试类别 | 测试项 | 状态 |
|---------|--------|------|
| API 健康检查 | GET /api/models | ✅ |
| | GET /api/images | ✅ |
| | GET /api/prompts | ✅ |
| | GET /api/tasks/queue | ✅ |
| 图片 CRUD | 列表 | ✅ |
| | 批量删除 | ✅ |
| Prompt CRUD | 创建/列表/更新/删除 | ✅ |
| Prompt 增强 | 中英文优化 | ✅ |
| 模型管理 | 扫描/列表/设置默认 | ✅ |
| 生成 - 默认 | 队列/完成/路径/可访问 | ✅ |
| 生成 - 带参数 | 队列/完成 | ✅ |
| 图生图 | 上传/队列/完成 | ✅ |
| UI 导航 | 7 个路由 | ✅ |
| 侧边栏 | 7 个菜单项 | ✅ |
| Text2Img 表单 | textarea/按钮/滑块/下拉 | ✅ |
| Img2Img 表单 | 上传区/按钮 | ✅ |
| Prompt 管理页 | 新建按钮/分类 tabs | ✅ |
| 设置页 | 保存按钮/主题开关 | ✅ |
| 深色模式 | 切换开/关 | ✅ |
