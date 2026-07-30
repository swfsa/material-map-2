from sqlmodel import Session, select

from models import MaterialRecord



class MaterialRepository:


    def __init__(
        self,
        session:Session
    ):

        self.session=session


    """
    根据 sub_category 精确匹配；
    按 period 从新到旧排序；
    默认最多返回 20 条。
    """
    def query_material(
        self,
        sub_category:str,
        limit:int=20
    ):
        statement = (
            select(MaterialRecord)
            .where(
                MaterialRecord.sub_category
                ==
                sub_category
            )
            .order_by(
                MaterialRecord.period.desc()
            )
            .limit(limit)

        )


        result = self.session.exec(
            statement
        )

        return result.all()