from database import get_session
from sqlmodel import select

from models import MaterialRecord


session=get_session()


stmt=select(MaterialRecord)


result=session.exec(stmt)


for row in result:

    print(
        row.sub_category,
        row.value
    )