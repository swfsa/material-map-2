# 物资地图 2.0 Backend 当前实现与限制

本文档以 `E:\code\cargo2.0\backend` 当前代码和本地验证结果为准，重点说明：

1. 现在已经实现了什么；
2. PoC3、PoC4 之间怎样协作；
3. 如何启动、导入和验证；
4. 哪些仍然只是系统设计目标，尚未落地。

> 当前 backend 使用 Python 3.14、Pydantic AI、SQLModel、FastAPI 和 MySQL。设计计划中的目标数据库是 PostgreSQL，但本 PoC 当前仍使用 MySQL。

## 1. 当前完成度概览

| 模块 | 当前状态 | 说明 |
|---|---|---|
| PoC3 内部数据查询 | 已实现 | Agent 可按 `sub_category`、日期、地区和数量查询 `material_records` |
| PoC3 Web Search | 已实现 | 支持 Tavily，DDGS 作为备用实现 |
| 多 LLM Provider | 已实现 | 支持 DeepSeek、百炼、MiMo、Anthropic 和通用兼容 Provider |
| 结构化简报 `ReportIR` | 已实现 | 仅允许 `heading/paragraph/kpiGrid/callout/table` 五类 block |
| ReportIR 持久化 | 已实现 | 按内容 SHA-256 幂等写入 `report_ir` |
| EIA 确定性分析 | 已实现 | 状态、7/30日变化、趋势、30日波动率、分位数、回撤和风险规则 |
| EIA 全序列导入 | 已实现并完成真实导入 | 14 个 series 按统一业务字段映射，API 不暴露 EIA 专属 `series` |
| `GET /api/records` | 已实现 | 支持分类、来源、日期筛选，返回稳定前端契约并流式发送 JSON 数组 |
| `GET /api/reports/latest` | 已实现 | 返回 `{report_ir, html, generated_at}`；兼容读取旧报告行 |
| `POST /api/ingest` | 未实现 | 目前写入来自 CLI 导入器，不通过 HTTP 写入 |
| `GET /api/analysis` | 未实现 | 尚无 `analysis_history` 表和统计分析写入链路 |
| 自动数据源 Adapter | 未实现 | 尚无统一 `BaseSource.fetch → parse → validate → store → run` 框架 |
| Alembic 数据库迁移 | 未实现 | `report_ir` 目前使用 `create_all(checkfirst)` 创建 |
| GDACS | 未接入 | 灾害数据尚未进入独立事件模型和 API |

## 2. 当前目录职责

```text
backend/
├── .env                      # 本地真实配置，不应提交 Git
├── .env.example2             # 配置模板，不包含真实密钥
├── pyproject.toml            # Python 依赖与 pytest 配置
├── uv.lock                   # uv 锁定依赖
├── poc3/
│   ├── agent.py              # Pydantic AI Agent 和生成规则
│   ├── tools.py              # query_material、web_search 工具
│   ├── deps.py               # Agent 依赖容器
│   ├── llm_factory.py        # LLM Provider/协议配置与模型工厂
│   ├── search_factory.py     # Tavily/DDGS 搜索工厂
│   ├── repository.py         # 物资查询与 ReportIR 持久化
│   ├── report.py             # ReportIR、证据、冲突等结构化模型
│   ├── models.py             # material_records、report_ir 表模型
│   ├── response_models.py    # 前端 API 专用响应模型
│   ├── import_data.py        # 通用 JSON 幂等导入器
│   ├── eia_import.py         # staging_eia → material_records 全序列导入
│   ├── import_report.py      # JSON/TXT ReportIR 幂等导入
│   ├── main.py               # Agent CLI：分析、生成、保存 ReportIR
│   └── tests/                # PoC3 离线测试
└── poc4/
    ├── main.py               # FastAPI 路由
    ├── repository.py         # API 只读查询
    ├── database.py           # 每请求 Session
    ├── verify_mysql_api.py   # 真实 MySQL records API 验证
    ├── verify_mysql_report_api.py
    └── tests/                # PoC4 API 测试
```

`backup/` 中的 SQL 文件属于源数据备份，不是业务库运行时表。原始 SQL 不应直接对业务库执行。

## 3. 当前数据流

```mermaid
flowchart LR
    SQL["EIA SQL 备份"] --> STAGING["staging_eia.eia_data"]
    STAGING --> IMPORT["poc3.eia_import<br/>映射 + 校验 + 幂等写入"]
    JSON["统一 JSON 数据"] --> GENERIC["poc3.import_data"]
    GENERIC --> DB[("MySQL material_records")]
    IMPORT --> DB

    DB --> REPO["MaterialRepository"]
    REPO --> TOOL["query_material 工具"]
    WEB["Tavily / DDGS"] --> SEARCH["web_search 工具"]
    TOOL --> AGENT["Pydantic AI Agent"]
    SEARCH --> AGENT
    AGENT --> REPORT["ReportIR 校验"]
    REPORT --> REPORTDB[("report_ir")]

    DB --> API1["GET /api/records"]
    REPORTDB --> API2["GET /api/reports/latest"]
    API1 --> FRONT["Vue / ECharts 前端"]
    API2 --> FRONT
```

## 4. PoC3 已实现功能

### 4.1 内部数据查询工具

Agent 注册了 `query_material` 工具，支持：

- `sub_category` 分类筛选；
- `start_date`、`end_date` 日期范围；
- `region` 精确地区筛选；
- `limit` 1～100 条限制；
- 按时间倒序获取最新记录。

当前允许 Agent 查询的 EIA 相关分类包括：

- `crude_oil`
- `diesel`
- `gasoline`
- `natural_gas`
- `natural_gas_storage`
- `natural_gas_storage_salt`
- `natural_gas_storage_nonsalt`

Repository 使用“每次查询创建并关闭一个 Session”的方式，避免 Pydantic AI 并发调用同步工具时共享同一个 SQLModel Session。

### 4.2 外部网页搜索

`web_search` 工具目前支持：

- Tavily：默认 Provider，支持超时、重试、搜索深度和主题配置；
- DDGS：不需要 Tavily Key，可作为备用搜索实现；
- 标准化搜索结果；
- 保留标题、摘要、URL、来源和检索时间；
- 将 Provider 异常转换为统一搜索错误。

Agent 规则要求先查内部数据，只有解释最新事件、政策、供应中断或内部数据无法解释原因时再调用外部搜索。

### 4.3 多模型配置

`llm_factory.py` 支持：

- DeepSeek；
- 阿里云百炼；
- 小米 MiMo；
- Anthropic；
- OpenAI-compatible / Anthropic-compatible 自定义 Provider；
- MiMo 等 Provider 在 OpenAI 和 Anthropic 协议间切换。

Agent 本身不直接依赖某个厂商，模型、Base URL、API Key 和协议通过 `.env` 配置。

### 4.4 结构化简报 ReportIR

Agent 不再负责填写 KPI。Python 分析器先计算数值，Agent 只输出经过 Pydantic 校验的 `EnergyNarrative`，随后 `ReportBuilder` 组装统一 `ReportIR`：

```text
ReportIR
└── blocks[]
    ├── heading
    ├── paragraph
    ├── kpiGrid
    ├── callout
    └── table
```

已经实现的约束包括：

- block 类型、data 字段和 table 列都严格校验；
- 外部证据必须有 URL，冲突单独记录；
- KPI/table 数值只来自确定性分析结果；
- HTML 从合法 block 转义生成，不接受模型输出的任意 HTML；
- Agent 叙述缺字段或类型错误时由 Pydantic AI 重试；
- 相同 ReportIR 按内容 SHA-256 幂等保存，不重复写库。

### 4.5 EIA 全量导入

当前 EIA dump 中的 14 个 series 已全部建立业务映射，源端 `series` 只用于：

- 选择正确的分类、单位、区域和指标类型；
- 生成 `eia|{series}|{period}` 对应的稳定 UUID v5；
- 保存到内部 `raw_metadata` 供审计追溯。

API 不增加 `series` 字段。业务含义由以下标准字段表达：

```text
category + sub_category + region + metric_type + unit
```

主要映射包括：

| 来源指标 | category | sub_category | metric_type | 标准单位 |
|---|---|---|---|---|
| WTI、Brent 原油价格 | `energy` | `crude_oil` | `price` | `USD/barrel` |
| 美国原油库存 | `energy` | `crude_oil` | `volume` | `thousand_barrels` |
| Henry Hub 天然气价格 | `energy` | `natural_gas` | `price` | `USD/MMBtu` |
| 天然气区域库存 | `energy` | `natural_gas_storage*` | `volume` | `billion_cubic_feet` |
| 柴油零售价 | `energy` | `diesel` | `price` | `USD/gallon` |
| 汽油零售价 | `energy` | `gasoline` | `price` | `USD/gallon` |

本地正式导入验收结果：

- staging 原始行：40,218；
- 可转换非空值：40,217；
- Henry Hub 有 1 条 `value=NULL`，按契约跳过；
- 本轮新增：30,003；
- 已有 WTI unchanged：10,214；
- 更新：0；
- 业务库当前 `source=eia`：40,219，其中含原有 2 条冻结样本；
- staging 有效业务键缺失：0；
- 重复 `record_id`：0；
- 必填业务字段空值：0。

这些数字是当前本地数据库的验收快照，不应被当成未来环境的固定常量。

## 5. PoC4 已实现功能

### 5.1 GET /api/records

支持以下可选参数：

```http
GET /api/records?category=X&sub_category=X&source=X&period_from=YYYY-MM-DD&period_to=YYYY-MM-DD
```

行为：

- 日期范围两端都包含；
- 开始时间晚于结束时间时返回 422；
- 结果按 `period`、数据库 `id` 升序；
- 数据库分批读取，每批默认 100 行；
- 使用 `StreamingResponse` 输出标准 JSON 数组；
- 响应不暴露数据库内部 `id`、`record_id`、`raw_metadata`、`fetched_at`；
- EIA 原始 `series` 不属于公开 API 契约。

返回字段：

```text
category, sub_category, region, metric_type, value, unit, period,
confidence, geo_scale, geo_ref, source, source_url, mom_change, yoy_change
```

### 5.2 GET /api/reports/latest

行为：

- 查询 `report_ir` 中最近生成的一份报告；
- 从数据库 JSON 重新执行 block `ReportIR` 校验；旧字段式报告会在读取时转换；
- 后端从合法 block 确定性生成转义后的 HTML；
- 返回数据库行的 UTC `generated_at`；
- 没有报告时返回 404；
- 不暴露 `id`、`content_sha256` 等内部字段。

响应固定为：

```json
{
  "report_ir": {"blocks": []},
  "html": "<article>...</article>",
  "generated_at": "2026-08-06T10:30:00Z"
}
```

### 5.3 数据库与 API 模型隔离

`MaterialRecord` 是数据库表模型；`MaterialIntelRecord` 是独立的公开响应模型。两者通过显式 mapper 转换，避免把 ORM 行或内部审计字段直接返回给前端。

## 6. 环境配置

在 `backend/.env` 配置真实值，不要把密钥提交到 Git：

```dotenv
# 业务数据库
DATABASE_URL=mysql+pymysql://APP_USER:PASSWORD@localhost:3306/material_intelligence

# 只读 EIA staging
EIA_SOURCE_DATABASE_URL=mysql+pymysql://READ_ONLY_USER:PASSWORD@localhost:3306/staging_eia

# LLM
LLM_PROVIDER=deepseek
LLM_API_STYLE=openai
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 搜索
WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=
```

密码如果包含 `@`、`:`、`#`、`%` 等 URL 特殊字符，需要进行 URL 编码。

PyCharm 建议配置：

```text
Interpreter:
E:\code\cargo2.0\backend\.venv\Scripts\python.exe

Working directory:
E:\code\cargo2.0\backend
```

并将 `backend` 标记为 Sources Root。

## 7. 常用运行命令

所有命令均在 `E:\code\cargo2.0\backend` 下执行。

### 7.1 安装/同步依赖

```powershell
uv sync
```

### 7.2 启动 PoC4 API

```powershell
.\.venv\Scripts\python.exe -m uvicorn poc4.main:app --reload
```

Swagger：<http://127.0.0.1:8000/docs>

### 7.3 运行 Agent 并保存 ReportIR

```powershell
.\.venv\Scripts\python.exe -m poc3.main
```

当前 `poc3.main` 中的业务问题仍是代码内固定的 `crude_oil` 分析示例。

### 7.4 导入 EIA

少量预检，每个 series 最多 10 条，不写业务库：

```powershell
.\.venv\Scripts\python.exe -m poc3.eia_import --all-series --limit 10 --dry-run
```

全量预检：

```powershell
.\.venv\Scripts\python.exe -m poc3.eia_import --all-series --batch-size 1000 --dry-run
```

正式幂等导入：

```powershell
.\.venv\Scripts\python.exe -m poc3.eia_import --all-series --batch-size 1000
```

正式导入后再次运行全量 `--dry-run`，所有有效源记录应为 `unchanged`。

### 7.5 导入已有 ReportIR

```powershell
.\.venv\Scripts\python.exe -m poc3.import_report "报告文件.json"
```

### 7.6 真实 MySQL 验证

```powershell
.\.venv\Scripts\python.exe -m poc4.verify_mysql_api --category energy
.\.venv\Scripts\python.exe -m poc4.verify_mysql_report_api
```

## 8. 测试状态

离线测试使用 SQLite 和 Stub/Fake，不要求真实 MySQL、LLM 或搜索网络：

```powershell
.\.venv\Scripts\python.exe -m pytest poc3\tests -q
.\.venv\Scripts\python.exe -m pytest poc4\tests -q
```

当前回归结果：

```text
PoC3：53 passed
PoC4：9 passed
```

覆盖范围包括：

- Repository 日期、地区、limit 和并发 Session；
- Agent 工具调用和结构化输出重试；
- LLM Provider/协议配置；
- Tavily/DDGS 正常与失败路径；
- ReportIR 校验、哈希和幂等持久化；
- 流式 JSON 编码；
- EIA 14 个 profile、全量入口、空值过滤和幂等导入；
- EIA staging → PoC3 → PoC4 跨模块契约；
- API 参数、响应字段、排序、404 和 OpenAPI 契约。

## 9. 当前限制

### 9.1 数据接入仍是手动批处理

EIA 已经可以全量、分批、幂等导入，但当前输入仍是人工恢复到 `staging_eia` 的 SQL 数据。尚未实现系统设计中的：

```text
BaseSource.fetch → parse → validate → store → run → cron
```

因此当前不是自动定时抓取 EIA API 的生产数据管线。

### 9.2 PoC4 只有读取接口

当前只有：

- `GET /api/records`
- `GET /api/reports/latest`

尚未实现设计计划中的：

- `POST /api/ingest`
- `GET /api/analysis`
旧 `/api/ReportIR` 只作为临时兼容路由保留，并从 OpenAPI 隐藏。

### 9.3 已有最小能源统计分析层

当前已实现：

- 14 个 EIA 内部指标注册与精确时序查询；
- 最新状态、7/30日变化、30日均值；
- 按推断频率年化的30日波动率；
- Z-score、窗口分位数、最大回撤和趋势；
- 样本不足、统计异常、高波动、较大回撤、数据过期风险规则。

仍未实现：

- STL 分解；
- 相关性分析；
- ARIMA 预测；
- `analysis_history` 表；
- 异常点持久化和 `/api/analysis`。

当前分析结果在报告生成过程中计算并写入 ReportIR，不单独持久化为 analysis_history。

### 9.4 mom_change / yoy_change 尚未计算

EIA 导入记录的 `mom_change`、`yoy_change` 当前为 `null`。项目没有擅自生成没有明确公式、频率对齐和缺失值规则的环比同比结果。

### 9.5 API 缺少进一步的查询控制

`/api/records` 当前没有：

- `region` 查询参数；
- `metric_type` 查询参数；
- 分页、cursor 或最大返回数量；
- 聚合和降采样。

虽然数据库采用分批读取和流式响应，但不加筛选请求全部记录时，客户端最终仍需接收完整 JSON 数组。

WTI 与 Brent 都属于 `energy/crude_oil/price`，目前由响应中的 `region` 区分；前端 WTI 图在客户端按 `region=US-OK-CUSHING` 继续筛选。

### 9.6 数据库迁移体系未建立

当前使用 MySQL，而设计计划写的是 PostgreSQL；这是 PoC 阶段的实现偏差。项目也尚未接入 Alembic：

- `material_records` 被视为已有表；
- `report_ir` 通过 `create_all(checkfirst)` 创建；
- 没有版本化升级、降级和环境迁移记录。

### 9.7 Agent 入口仍是固定示例

`poc3.main` 中的问题目前固定为“分析 crude_oil 最近价格态势”。尚未实现：

- HTTP 报告生成端点；
- 用户动态输入；
- 后台任务和进度查询；
- 定时简报调度；
- 失败任务恢复或队列。

### 9.8 外部服务依赖

真实 Agent/搜索运行依赖：

- 正确的 API Key、模型名和 Base URL；
- 外部网络可用；
- Provider 支持工具调用和结构化输出；
- 供应商配额、费用和限流。

离线测试通过不代表外部 Provider 当前一定可用；真实协议验证需要单独执行 verifier。

### 9.9 尚无生产安全能力

当前 FastAPI 未实现：

- 登录鉴权和权限控制；
- API 限流；
- CORS 白名单配置；
- 审计日志和操作人；
- 统一监控、指标和告警；
- 面向多实例部署的任务协调。

因此当前适合本地 PoC 和联调，不应直接作为公开生产服务部署。

### 9.10 其他数据源未形成闭环

- GDACS 尚未接入；灾害数据不应直接塞入 `material_records`，后续需要独立事件模型。
- Open-Meteo、FAO adapter 尚未出现在当前 backend。
- EIA dump 没有可靠抓取时间，因此导入器保留 `fetched_at=null`，不会伪造采集时间。
- EIA 分类映射目前由代码中的 profile 手动维护；源端新增 series 时需要先审计并新增映射和测试。

## 10. 推荐的下一步顺序

结合当前主要负责的 PoC3、PoC4，建议按以下顺序继续：

1. 为新 `report_ir` 合同建立 Alembic 版本迁移和旧行一次性迁移脚本；
2. 设计报告生成 API/后台任务状态，不在 GET 中执行 LLM；
3. 根据需要增加 `analysis_history` 和 `GET /api/analysis`；
4. 为 `/api/records` 增加 `region`、`metric_type` 和安全分页/limit；
5. 实现 `POST /api/ingest`，复用现有校验与幂等逻辑；
6. 抽取统一 BaseSource，再将 EIA 从 SQL staging 批处理升级为可调度 Adapter；
7. EIA 闭环稳定后，再以独立灾害事件模型接入 GDACS。

## 11. 当前结论

当前 backend 已经打通以下真实闭环：

```text
EIA staging
→ 统一业务字段映射
→ MySQL material_records
→ 确定性状态/趋势/波动/风险分析
→ Agent 生成叙述和外部证据
→ ReportBuilder 组装五类 block
→ 可选 Web Search
→ Pydantic ReportIR
→ report_ir 持久化
→ GET /api/reports/latest
→ 前端消费
```

它已经可以作为 EIA 能源简报的真实数据和接口验证基础，但距离生产服务仍有差距，主要缺口是自动 Adapter、写入 API、分析历史、迁移体系、任务化报告生成与生产安全能力。
