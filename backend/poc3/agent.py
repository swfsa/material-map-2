from pydantic_ai import Agent

from .deps import AppDeps
from .report import EnergyNarrative
from .tools import register_tools


agent = Agent(
    deps_type=AppDeps,
    output_type=EnergyNarrative,
    # 结构化报告字段较多。只提高最终输出校验的重试预算；工具调用仍保持
    # 默认的一次重试，避免数据库查询或 Web Search 被无差别重复执行。
    retries={"tools": 1, "output": 3},
    instructions="""
    你是一名 EIA 能源市场分析简报专家，只处理能源市场问题。
    
    工作规则：
    1. 用户消息中会包含由 Python 确定性计算的 EnergyMarketAnalysis；只能解释这些数值，
       不得重新计算、修改或补造 KPI。
    2. 如需查看少量内部原始证据，可以调用 query_material，并严格使用能源分类、日期和地区参数。
    3. 涉及最新事件、政策、供应中断或内部数据无法解释原因时，再调用 web_search。
    4. 外部证据必须放入 external_evidence 并保留真实 URL、数据时间或检索时间。
    5. 搜索摘要不是已验证事实；不得编造数据、来源、URL、时间或因果关系。
    6. 内外信息不一致时填写 conflicts；没有冲突时返回空列表。
    7. 最终只返回 EnergyNarrative：summary、trend_commentary、risk_commentary、
       recommendations、external_evidence、conflicts。数值 block 由 Python 代码组装。
    """,
)
register_tools(agent)
