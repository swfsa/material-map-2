from pydantic_ai import RunContext

from deps import AppDeps



def register_tools(agent):

    @agent.tool
    def query_material(
            ctx: RunContext[AppDeps],
            sub_category: str
    ):
        """
        查询物资数据库。

        可查询类别:
        - crude_oil
        - food_price_index
        - surface_weather

        不要使用商品名称缩写。
        """

        repo = ctx.deps.material_repo


        records = repo.query_material(
            sub_category
        )


        return [

            {
            "period":str(r.period),
            "value":r.value,
            "unit":r.unit,
            "region":r.region,
            "source":r.source
            }

            for r in records

        ]