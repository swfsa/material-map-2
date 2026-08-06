# PoC3：EIA 数据导入、能源分析与结构化简报

PoC3 是 `cargo2.0` 后端的分析与报告生成模块，负责把原始能源数据转换为统一业务记录，完成确定性能源分析，再由 Pydantic AI Agent 生成可追溯的文字简报和 `ReportIR`。

PoC3 不提供 HTTP 报告生成接口。报告生成通过 CLI 或显式导入执行；PoC4 负责以只读 API 向前端提供记录和最新报告。

## 1. 当前能力概览

```text
EIA staging / JSON
        ↓
  字段映射、校验、幂等导入
        ↓
  MySQL material_records
        ↓
  完整能源时序查询
        ↓
  Python 确定性分析
        ↓
  Pydantic AI Agent 生成叙述
        ↓
  ReportBuilder 组装 ReportIR
        ↓
  report_ir 表幂等保存
        ↓
  PoC4 GET /api/reports/latest
```

当前已经实现：

- 通用 JSON 数据导入和 EIA staging 全序列导入；
- `MaterialRecord` 统一数据模型和 MySQL 持久化；
- 按分类、日期、地区查询内部数据；
- WTI、Brent、天然气、汽柴油、天然气库存等能源指标注册；
- 最新值、7/30 日变化、30 日均值、波动率、Z-score、分位数、最大回撤和趋势分析；
- 样本不足、统计异常、高波动、大回撤、数据过期等风险规则；
- Pydantic AI Agent、`query_material`、`web_search` 工具；
- Tavily 默认搜索和 DDGS 备用搜索；
- DeepSeek、百炼、MiMo、Anthropic 及兼容协议 Provider 配置；
- 严格校验的 `ReportIR`、安全 HTML 渲染和 SHA-256 幂等保存；
- 旧版字段式报告到 block 式报告的兼容导入/读取。

当前尚未实现：

- `POST /api/ingest` HTTP 写入接口；
- `GET /api/analysis` 和 `analysis_history` 持久化；
- 自动化 `fetch → parse → validate → store → run → cron` 数据源框架；
- GDACS 灾害事件模型和 API；
- STL、相关性、ARIMA 预测；
- 报告定时任务、队列、任务状态查询和生产级鉴权/限流。

## 2. 模块设计

### 2.1 分层结构

```mermaid
flowchart TB
    SOURCE["EIA staging / JSON"] --> IMPORT["eia_import.py / import_data.py"]
    IMPORT --> RECORDS[("MySQL material_records")]
    RECORDS --> REPO["Repository"]
    REPO --> CALC["energy_analysis.py"]
    CALC --> ANALYSIS["EnergyMarketAnalysis"]
    ANALYSIS --> AGENT["Pydantic AI Agent"]
    REPO --> TOOL1["query_material"]
    SEARCH["Tavily / DDGS"] --> TOOL2["web_search"]
    TOOL1 --> AGENT
    TOOL2 --> AGENT
    AGENT --> NARRATIVE["EnergyNarrative"]
    ANALYSIS --> BUILDER["report_builder.py"]
    NARRATIVE --> BUILDER
    BUILDER --> IR["ReportIR"]
    IR --> REPORTDB[("report_ir")]
```

### 2.2 责任边界

| 部分 | 责任 |
|---|---|
| `eia_import.py` | 从独立 staging 库读取 EIA，映射统一业务字段并批量导入 |
| `import_data.py` | 处理通用 JSON，校验字段并按 `record_id` 幂等写入 |
| `repository.py` | 封装数据库查询；每次 Agent 查询使用独立 Session |
| `energy_registry.py` | 将 EIA series 注册为业务指标 Profile |
| `energy_analysis.py` | 只负责确定性数值计算和风险规则 |
| `agent.py` | 定义 Agent 的领域规则和 `EnergyNarrative` 输出约束 |
| `tools.py` | 注册内部数据查询和外部搜索工具 |
| `llm_factory.py` | 读取 Provider 配置并创建模型 |
| `search_factory.py` | 按配置选择 Tavily 或 DDGS |
| `report_builder.py` | 使用分析结果和 Agent 叙述组装五类 ReportIR block |
| `report_renderer.py` | 将已校验的 ReportIR 转成安全 HTML |
| `ReportRepository` | 用内容 SHA-256 避免重复保存报告 |

核心设计原则：Python 计算数字，Agent 负责文字；Agent 不直接生成 KPI，也不返回任意 HTML。

## 3. 目录与文件职责

```text
backend/poc3/
├─ main.py                  # 生成并保存能源简报的 CLI 入口
├─ agent.py                 # Pydantic AI Agent 和系统规则
├─ tools.py                 # query_material、web_search 工具
├─ deps.py                  # Agent 依赖容器
├─ domain.py                # 分类、搜索时间范围等 Literal
├─ config.py                # 环境变量读取和配置错误
├─ llm_factory.py           # 多 Provider / 多协议模型工厂
├─ database.py              # Engine、Session、report_ir 建表
├─ models.py                # MaterialRecord、ReportIRRecord
├─ repository.py            # 数据查询和报告持久化
├─ import_data.py           # 通用 JSON 导入器
├─ eia_import.py            # EIA staging 全序列导入器
├─ energy_registry.py       # EIA 指标注册表
├─ energy_analysis.py       # 确定性能源分析
├─ report_service.py        # 分析 → Agent → 报告的编排
├─ report.py                # ReportIR、EnergyNarrative 等契约
├─ report_builder.py        # 组装 heading/paragraph/KPI 等 blocks
├─ report_renderer.py       # ReportIR → HTML
├─ import_report.py         # JSON/TXT ReportIR 幂等导入
├─ search_models.py         # SearchResult 和 WebSearchClient Protocol
├─ search_factory.py        # 搜索客户端工厂
├─ tavily_search.py         # Tavily 适配器
├─ web_search.py            # DDGS 备用适配器
└─ tests/                   # 离线单元测试和契约测试
```

## 4. 技术栈

| 技术 | 用途 |
|---|---|
| Python 3.14+ | 后端运行时 |
| uv | 依赖安装和锁定 |
| FastAPI | PoC4 API 层 |
| SQLModel / SQLAlchemy | ORM、SQL 查询、Engine、Session |
| MySQL / PyMySQL | 当前 PoC 业务数据库 |
| Pydantic v2 | 数据、Agent 输出和 ReportIR 校验 |
| Pydantic AI | Agent、工具调用、依赖注入 |
| Tavily / DDGS | 外部公开网页搜索 |
| pytest | 后端离线和集成测试 |

设计目标数据库是 PostgreSQL，但当前 PoC 实际连接仍以 MySQL 为准，尚未接入 Alembic 版本迁移。

## 5. 环境配置

在 `backend/.env` 中配置真实值；不要把密钥和密码写进 README 或提交 Git。

```dotenv
DATABASE_URL=mysql+pymysql://APP_USER:PASSWORD@localhost:3306/material_intelligence
EIA_SOURCE_DATABASE_URL=mysql+pymysql://READ_ONLY_USER:PASSWORD@localhost:3306/staging_eia

LLM_PROVIDER=deepseek
LLM_API_STYLE=openai
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=
DEEPSEEK_BASE_URL=https://api.deepseek.com

WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=
WEB_SEARCH_TIMEOUT=30
TAVILY_MAX_RETRIES=1
TAVILY_RETRY_DELAY=1
```

已支持的模型配置方向包括 DeepSeek、阿里云百炼、MiMo、Anthropic，以及通用 OpenAI-compatible / Anthropic-compatible 地址。`LLM_PROVIDER` 只决定大模型，`WEB_SEARCH_PROVIDER` 只决定搜索客户端。

搜索客户端：

```dotenv
# Tavily，默认模式
WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=...

# 或切换到不依赖 Tavily Key 的 DDGS
WEB_SEARCH_PROVIDER=ddgs
WEB_SEARCH_REGION=wt-wt
WEB_SEARCH_SAFESEARCH=moderate
WEB_SEARCH_BACKEND=auto
```

外部证据必须保留真实 URL。搜索摘要不是已验证事实，Agent 不得编造来源、时间或因果关系。

## 6. 数据模型与导入

### 6.1 MaterialRecord

业务表 `material_records` 的核心字段：

```text
record_id       稳定业务记录 ID
category        一级分类，如 energy
sub_category    子分类，如 crude_oil
region          标准地区，如 US-OK-CUSHING
metric_type     price / volume
value           数值
unit            单位
period          数据时间
source          数据源，如 eia
source_url      来源 URL
confidence      可信度标记
geo_scale       地理粒度
geo_ref         结构化地理信息
raw_metadata    源字段和追溯信息
```

当前 `domain.py` 支持的查询分类包括：

```text
crude_oil
diesel
food_price_index
gasoline
natural_gas
natural_gas_storage
natural_gas_storage_nonsalt
natural_gas_storage_salt
surface_weather
```

### 6.2 通用 JSON 导入

```powershell
cd E:\code\cargo2.0\backend
uv run python -m poc3.import_data poc3\data.json --dry-run
uv run python -m poc3.import_data poc3\data.json
```

导入器根据稳定 `record_id` 判断新增、更新或 unchanged，重复运行不会产生重复记录。

### 6.3 EIA staging 导入

原始 EIA dump 必须先恢复到独立的 `staging_eia`，不要直接对业务库执行原始 SQL。

```powershell
# 小批量预检，不写业务库
uv run python -m poc3.eia_import --all-series --limit 10 --dry-run

# 全量预检
uv run python -m poc3.eia_import --all-series --batch-size 1000 --dry-run

# 正式导入
uv run python -m poc3.eia_import --all-series --batch-size 1000
```

导入完成后再次执行全量 `--dry-run`，可转换记录应全部为 `unchanged`。

常用筛选参数：

```powershell
# 只导入 WTI
uv run python -m poc3.eia_import --series RWTC --batch-size 1000

# 限定时间范围
uv run python -m poc3.eia_import --series RWTC --period-from 2026-01-01 --period-to 2026-07-31 --dry-run
```

导入器当前支持已注册的 14 个 EIA series。源端 `series` 用于选择映射和生成稳定业务键，公共 API 不暴露该字段；原始 series 信息保存在 `raw_metadata`。

稳定业务键使用 UUID v5：

```text
eia|{series}|{period}
```

空 `value` 记录会被跳过，不会伪造数值；dump 没有可靠抓取时间时，不会编造 `fetched_at`。

## 7. 内部查询与 Agent 工具

### 7.1 query_material

```python
query_material(
    sub_category,
    start_date=None,
    end_date=None,
    region=None,
    limit=20,
)
```

约束：`sub_category` 必须是合法分类；日期两端包含；`start_date` 不能晚于 `end_date`；`limit` 为 1～100；结果按时间倒序返回。

### 7.2 Session 隔离

Pydantic AI 可能在线程池中并行执行同步工具。PoC3 使用 `SessionPerQueryMaterialRepository` 和 `SessionPerQueryEnergyRepository`，让每次查询独立创建和关闭 Session，避免跨线程共享 SQLAlchemy Session。

### 7.3 web_search

```python
web_search(query, max_results=5, time_limit=None)
```

`max_results` 限制为 1～10；`time_limit` 可使用 `d`、`w`、`m`、`y`。工具依赖 `WebSearchClient` Protocol，因此测试可以使用 Fake Client，生产环境可以在 Tavily 和 DDGS 之间切换。

Agent 规则是：先使用内部数据；只有在需要解释最新事件、政策、供应中断，或内部数据无法解释原因时，才调用外部搜索。

## 8. 确定性能源分析

`energy_registry.py` 使用 Profile 描述指标：`indicator_id`、`display_name`、`series`、业务分类、地区、指标类型、单位和来源 URL。

WTI 的业务映射为：

```text
series        RWTC
category      energy
sub_category  crude_oil
region        US-OK-CUSHING
metric_type   price
unit          USD/barrel
```

`energy_analysis.py` 对每个指标计算：

1. 最新值和前一值；
2. 7 日、30 日变化率；
3. 30 日移动平均；
4. 按推断频率年化的 30 日波动率；
5. 30 日 Z-score；
6. 分析窗口历史分位数；
7. 最大回撤；
8. up、down、flat 或 unknown 趋势；
9. 关联的源记录 ID。

风险规则包括：样本不足、统计异常、高波动、较大回撤和数据过期。所有分析结果进入 `EnergyMarketAnalysis`，再交给 Agent 解释。

## 9. ReportIR 与报告持久化

当前统一报告合同只允许五类 block：

```text
ReportIR.blocks[]
├── heading       标题
├── paragraph     摘要、趋势和风险说明
├── kpiGrid       数值指标卡片
├── callout       风险提示
└── table         统计、建议和证据表格
```

所有报告模型使用 `extra="forbid"`。外部证据必须提供 URL，表格列 key 必须唯一，表格行不能出现未声明列。

报告生成顺序：

```text
analyze_energy_market
        ↓
EnergyMarketAnalysis
        ↓
Agent.run_sync → EnergyNarrative
        ↓
build_energy_report
        ↓
ReportIR 校验
        ↓
ReportRepository.save
```

`EnergyNarrative` 只包含 Agent 负责的文字、建议、外部证据和冲突；KPI、统计表和风险 block 由 Python 的 `report_builder.py` 组装。

`ReportRepository` 对规范化后的 ReportIR JSON 计算 SHA-256，并以 `content_sha256` 唯一索引判断是否已经保存。旧版字段式报告可通过 `import_report.py` 导入，并在读取时转换为 blocks。

PoC4 读取最新报告时返回：

```json
{
  "report_ir": {"blocks": []},
  "html": "<article>...</article>",
  "generated_at": "2026-08-06T08:30:00Z"
}
```

## 10. 运行方式

所有命令从 `E:\code\cargo2.0\backend` 执行。

### 10.1 安装依赖

```powershell
uv sync
```

### 10.2 生成能源简报

```powershell
uv run python -m poc3.main
```

执行顺序：读取配置 → 查询完整能源时序 → 运行确定性分析 → 调用 Agent → 组装并校验 ReportIR → 创建 `report_ir` 表 → 按 SHA-256 幂等保存并打印 JSON。

当前入口默认分析最近一年，示例问题固定在代码中；动态用户问题和 HTTP 报告生成接口属于后续扩展。

### 10.3 导入已有报告

```powershell
uv run python -m poc3.import_report "C:\path\to\report.json"
```

支持当前 block 式 ReportIR，也兼容旧版字段式报告；重复导入不会重复写入。

### 10.4 独立验证外部服务

```powershell
uv run python -m poc3.verify_llm_api
uv run python -m poc3.verify_web_search
```

这两个命令需要真实 Provider 配置和网络，不能用离线 pytest 结果代替。

## 11. 测试与验证

### 11.1 PoC3 测试

```powershell
uv run pytest poc3\tests -q
```

当前仓库验证结果：

```text
62 passed
```

覆盖 Repository、Session 隔离、JSON/EIA 导入、能源分析、Agent 工具、Provider、Tavily/DDGS、ReportIR 构建/渲染和幂等持久化。

### 11.2 后端整体测试

```powershell
uv run pytest poc3\tests poc4\tests -q
```

当前仓库验证结果：

```text
72 passed
```

其中 PoC4 负责验证 `/api/records`、`/api/reports/latest` 及 staging → API 的集成链路。

## 12. 安全与运行边界

- `.env` 不提交 Git，示例配置只放占位符；
- 不在日志中打印数据库密码、完整连接 URL 或 API Key；
- EIA 原始 dump 先恢复到独立 staging，再导入业务库；
- EIA 导入使用只读源库连接和独立目标库连接；
- PoC4 使用 `MaterialIntelRecord`，不直接暴露 ORM 内部字段；
- 外部证据必须保留真实 URL；
- 离线测试通过不代表外部 LLM、Tavily、DDGS 或真实 MySQL 当前一定可用；
- 当前 API 尚未实现登录鉴权、限流、审计日志和生产级 CORS 白名单。

## 13. 常见问题

### 导入失败或没有数据

检查 `EIA_SOURCE_DATABASE_URL` 是否指向独立 staging 库、`DATABASE_URL` 是否指向业务库、staging 表是否为 `eia_data`、series 是否已注册，以及 `value` 是否为空。建议先执行 `--dry-run`。

### Agent 工具出现 Session 错误

不要把单个 `Session` 实例直接放进 `AppDeps` 供并发工具共享。使用 `get_session` 和 `SessionPerQueryMaterialRepository`，让每次查询独立管理 Session 生命周期。

### Provider 配置能 import 但运行失败

环境变量读取和调用时验证是两个阶段。未知 Provider 可能在模块 import 时不报错，但 `create_llm_model()` 或 `create_web_search_client()` 才会抛出配置错误。检查 Provider 名、协议、模型、Base URL 和 Key 是否属于同一服务。

### 为什么 PoC4 不生成报告

PoC4 当前只有只读接口：

```text
GET /api/records
GET /api/reports/latest
```

报告生成由 `python -m poc3.main` 或 `poc3.import_report` 完成。读取最新报告不会在 HTTP 请求中调用 Agent 或 Web Search。

## 14. 后续演进建议

1. 抽象自动化 Source Adapter 和调度任务；
2. 增加报告生成任务队列和任务状态；
3. 建立 `analysis_history`，保存分析版本和输入窗口；
4. 增加 Alembic 数据库迁移；
5. 增加 API 分页、聚合、鉴权、限流和审计；
6. 接入 GDACS 独立灾害事件模型；
7. 增加预测、相关性和跨品类分析；
8. 将真实 LLM、搜索和 MySQL smoke test 纳入受控集成环境。
