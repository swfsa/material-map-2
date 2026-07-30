from datetime import datetime
from typing import Optional, Any

from sqlalchemy import JSON
from sqlmodel import (
    SQLModel,
    Field
)



class MaterialRecord(SQLModel, table=True):

    __tablename__ = "material_records"

    #数据库自增主键
    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    #源记录唯一 ID，防止重复
    record_id: str = Field(
        index=True,
        unique=True
    )


    category: Optional[str]=None

    #子类，也是当前主要查询条件
    sub_category: Optional[str]=Field(
        default=None,
        index=True
    )


    region: Optional[str]=None

    #指标类型
    metric_type: Optional[str]=None

    #指标数值
    value: Optional[float]=None

    #单位
    unit: Optional[str]=None

    #数据所属时间
    period: Optional[datetime]=Field(
        default=None,
        index=True
    )

    #数据来源
    source: Optional[str]=None


    source_url: Optional[str]=None

    #数据所属时间
    confidence: Optional[str]=None

    #地理粒度
    geo_scale: Optional[str]=None

    #环比变化
    mom_change: Optional[float]=None

    #同比变化
    yoy_change: Optional[float]=None

    #抓取时间
    fetched_at: Optional[datetime]=None

    #来源特有的扩展元数据
    raw_metadata: Optional[dict[str,Any]]=Field(
        default=None,
        sa_type=JSON
    )

    #地理定位扩展信息
    geo_ref: Optional[dict[str,Any]]=Field(
        default=None,
        sa_type=JSON
    )