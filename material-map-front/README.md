# 物资地图前端：EIA WTI 对接

能源价格面板默认请求 `poc4` 的真实接口，不再默认使用 `src/mock/energyPrice.js`：

```text
GET /api/records?category=energy&sub_category=crude_oil&source=eia&period_from=...
```

## EIA 能源市场简报

点击大屏右侧“数据简报”后，前端读取统一接口：

```text
GET /api/reports/latest
```

响应中的 `report_ir.blocks` 是页面主数据源。前端会先校验合同，再分别渲染以下五类 block：

- `heading`：报告和章节标题；
- `paragraph`：分析正文与证据编号；
- `kpiGrid`：最新值、30 日变化、趋势、状态和数据时点；
- `callout`：信息、关注、预警和严重风险；
- `table`：趋势波动、建议、外部证据与计算方法。

`html` 仅作为后端导出/兼容字段，页面不使用 `v-html`。`generated_at` 会同步到简报元数据和大屏顶部“数据更新”时间。请求期间提供加载状态；404、合同错误和其他 HTTP 错误分别提示，并支持重新读取。离开简报时会取消未完成请求。

前后端分别启动时，开发环境可保留 `VITE_API_BASE_URL=`，由 Vite 把 `/api` 代理到 `http://127.0.0.1:8000`；跨域部署时将它设置为后端根地址。

前端验收命令：

```powershell
npm.cmd test
npm.cmd run build
```

## 本地联调

先在 `backend` 启动 API：

```powershell
uv run uvicorn poc4.main:app --reload
```

再在本目录启动前端：

```powershell
npm.cmd run dev
```

Vite 会把业务 `/api` 代理到 `http://127.0.0.1:8000`。面板显示“真实 EIA”才表示当前图表来自后端；接口失败会显示错误，不会静默换成 mock。

业务库可以同时保存 Brent、原油库存、天然气、成品油等其他 EIA 数据。WTI 面板会在 API 返回结果中继续按 `sub_category=crude_oil + metric_type=price + region=US-OK-CUSHING` 选择数据，因此不会把 Brent 或原油库存混进 WTI 曲线。API 响应保持统一 `MaterialIntelRecord` 契约，不增加 EIA 专属 `series` 字段。

只有需要独立开发前端时，才在 `.env.local` 中显式开启：

```dotenv
VITE_USE_MOCK_ENERGY=true
```

可选配置见 `.env.example`。运行验证：

```powershell
npm.cmd run test:energy
npm.cmd run build
```

Docker Desktop 版本的 `nginx.conf` 将业务 `/api/` 转发到宿主机 `8000`，并单独保留 `/api/geojson/` 的 DataV 代理。部署到其他环境时需要替换该 upstream。
