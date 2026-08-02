# poc4：MaterialRecord 与 ReportIR 查询 API

本目录验证当前链路中的 Read（CRUD 的 R）：

`HTTP GET -> FastAPI 参数校验 -> 每请求 SQLModel Session -> MySQL 分批读取 -> MaterialRecord 表实体 -> MaterialIntelRecord 响应模型 -> StreamingResponse`

并提供 ReportIR 链路：

`poc3 Agent/导入器 -> report_ir 表 -> GET /api/ReportIR -> ReportIR 合同校验 -> StreamingResponse`

两个接口都使用流式传输，但仍输出标准 `application/json`：`/api/records` 的最终结构仍是 JSON 数组，`/api/ReportIR` 仍是 JSON 对象，不是 SSE，也不是 NDJSON。已有的 `response.json()` 调用保持兼容。

`/api/records` 每批从数据库读取 100 行并逐条编码；`/api/ReportIR` 按顶层字段编码。响应不设置 `Content-Length`，并返回 `X-Accel-Buffering: no`，避免 Nginx 等代理把完整响应缓存后再一次性转发。

## 为什么需要单独的响应模型

数据库实体 `poc3.models.MaterialRecord` 还包含 `id`、`record_id`、`fetched_at`、`raw_metadata` 等内部字段。接口使用 `poc3.response_models.MaterialIntelRecord` 作为非表 SQLModel，只对前端暴露 14 个稳定字段。显式 mapper 是数据库结构与前端合同之间的过渡层。

## 启动

在项目根目录执行：

```powershell
uv sync
uv run uvicorn poc4.main:app --reload
```

Swagger UI：<http://127.0.0.1:8000/docs>

示例请求：

```text
GET http://127.0.0.1:8000/api/records?category=energy&period_from=2026-06-01&period_to=2026-07-31
```

`period_from`、`period_to` 使用 `YYYY-MM-DD`，两端都包含；所有筛选参数都可以省略。结果按 `period` 升序返回，便于前端直接绘制时序图。

如需让页面边接收边展示，前端必须读取 `fetch()` 返回值的 `response.body`；调用 `response.json()` 虽然兼容，但仍会等待整个 JSON 接收完成后才解析。命令行可用下面的方式直接观察响应流：

```powershell
curl.exe -N "http://127.0.0.1:8000/api/records?category=energy"
```

## 导入并查询 ReportIR

已有的 `.json` 或内容为 JSON 的 `.txt` 报告可以从项目根目录导入：

```powershell
.\.venv\Scripts\python.exe -m poc3.import_report "E:\code\poc3-1\poc3\report.txt"
```

导入器会先用 `poc3.report.ReportIR` 校验完整结构，再按内容 SHA-256 幂等写入。第一次输出 `created`；同一文件再次导入会输出 `already_exists`，不会产生重复行。首次导入会自动创建且只创建新的 `report_ir` 表。

以后运行 Agent：

```powershell
.\.venv\Scripts\python.exe -m poc3.main
```

Agent 成功生成 `ReportIR` 后也会自动保存。查询最近生成的一份报告：

```text
GET http://127.0.0.1:8000/api/ReportIR
```

接口逐字段发送完整 `ReportIR`，不暴露数据库内部的 `id`、`content_sha256`、`generated_at` 等字段。数据库没有报告时仍返回 `404 {"detail": "ReportIR not found"}`。

## 验证

离线 API 测试（SQLite，不依赖 MySQL）：

```powershell
uv run pytest poc4/tests -q
```

使用 `.env` 中配置的真实 MySQL 走完整 GET 链路：

```powershell
uv run python -m poc4.verify_mysql_api --category energy --period-from 2026-06-01 --period-to 2026-07-31
uv run python -m poc4.verify_mysql_report_api
```

当前范围只提供 GET/read；ReportIR 的写入来自 `poc3.main` 或显式导入命令，不通过 HTTP POST 暴露。
