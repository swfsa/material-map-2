from pydantic_ai import Agent

from config import DEEPSEEK_MODEL
from report import ReportIR
from deps import AppDeps
from tools import register_tools


agent = Agent(

    DEEPSEEK_MODEL,

    deps_type=AppDeps,

    output_type=ReportIR,

    defer_model_check=True,

    instructions="""

    你是物资态势分析专家。
    
    流程：
    
    1. 查询数据库
    2. 分析数据变化
    3. 必要时搜索外部信息
    4. 输出ReportIR
    
    禁止编造数据。
    
    """
)
register_tools(agent)
