from pydantic import BaseModel

class ReportIR(BaseModel):
    #标题
    title:str

    #摘要
    summary:str

    #关键发现
    key_findings:list[str]

    #风险
    risks:list[str]

    #建议
    suggestions:list[str]