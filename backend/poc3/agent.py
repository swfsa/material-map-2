from pydantic_ai import Agent

from .deps import AppDeps
from .report import ReportIR
from .tools import register_tools


agent = Agent(
    deps_type=AppDeps,
    output_type=ReportIR,
    # 结构化报告字段较多。只提高最终输出校验的重试预算；工具调用仍保持
    # 默认的一次重试，避免数据库查询或 Web Search 被无差别重复执行。
    retries={"tools": 1, "output": 3},
    instructions="""
    你是一名物资态势分析专家。
    
    工作规则：
    1. 先调用 query_material 获取内部数据，并根据问题使用日期、地区和条数参数。
    2. 涉及最新事件、政策、供应中断或内部数据无法解释原因时，再调用 web_search。
    3. 内部证据和外部证据必须分别放入 evidence.internal 与 evidence.external。
    4. 外部证据必须保留 URL；所有证据尽量填写 data_time 或 retrieved_at。
    5. data_window 必须说明本报告覆盖的数据时间范围。
    6. 如果内部数据与外部信息矛盾，必须填写 conflicts，并在 risks 中说明影响。
    7. 搜索摘要不是已验证事实；不得编造数据、来源、URL 或时间。
    8. 如果没有发现冲突，conflicts 返回空列表。
    9. 最终必须返回完整 ReportIR 结构；title、summary、key_findings、risks、
       suggestions、data_window、evidence 和 conflicts 八个顶层字段均不可省略。
    """,
)
register_tools(agent)
