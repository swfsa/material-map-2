# poc4：EIA 记录与统一能源简报读取 API

PoC4 提供两个只读接口：

```text
GET /api/records
GET /api/reports/latest
```

`GET /api/records` 分批读取 `material_records` 并流式返回标准 JSON 数组；`GET /api/reports/latest` 返回小型普通 JSON 对象，不在 GET 中调用 Agent、Web Search 或统计计算。

## 启动

在 `backend` 目录执行：

```powershell
uv sync
uv run uvicorn poc4.main:app --reload
```

Swagger UI：<http://127.0.0.1:8000/docs>

## 查询 EIA 记录

```text
GET /api/records?category=energy&sub_category=crude_oil&source=eia&period_from=2025-08-05
```

`category`、`sub_category`、`source`、`period_from`、`period_to` 都是可选参数。日期两端包含，结果按 `period`、数据库 `id` 升序。响应使用独立的 `MaterialIntelRecord`，不暴露 `id`、`record_id`、`raw_metadata`、`fetched_at` 或 EIA `series`。

## 查询最新能源简报

```text
GET /api/reports/latest
```

响应合同：

```json
{
  "report_ir": {
    "blocks": [
      {
        "type": "heading",
        "data": {"text": "EIA能源市场简报", "level": 1}
      }
    ]
  },
  "html": "<article class=\"energy-report\">...</article>",
  "generated_at": "2026-08-06T10:30:00Z"
}
```

- `report_ir` 只允许 `heading`、`paragraph`、`kpiGrid`、`callout`、`table`；
- `html` 由后端从已校验 block 转义生成，不使用模型返回的任意 HTML；
- `generated_at` 来自同一条数据库记录并转换为 UTC；
- 旧字段式 report_json 会在读取时转换为 blocks；
- 没有报告时返回 `404 {"detail":"Report not found"}`；
- 临时 `/api/ReportIR` 兼容路由仍可读取 block IR，但已从 OpenAPI 隐藏。

## 生成和保存报告

```powershell
uv run python -m poc3.main
```

生成顺序为：完整 EIA 时序查询 → Python 计算状态/趋势/波动/风险 → Agent 生成叙述和外部证据 → ReportBuilder 组装 blocks → SHA-256 幂等保存。

导入已有 block JSON或旧字段式 ReportIR：

```powershell
uv run python -m poc3.import_report "C:\path\to\report.json"
```

## 验证

离线测试：

```powershell
uv run pytest poc4/tests -q -p no:cacheprovider
```

使用 `.env` 中配置的真实 MySQL：

```powershell
uv run python -m poc4.verify_mysql_api --category energy --period-from 2026-06-01 --period-to 2026-07-31
uv run python -m poc4.verify_mysql_report_api
```

本轮没有实现报告生成 HTTP POST；报告写入仍来自 `poc3.main`、定时任务或显式导入。
