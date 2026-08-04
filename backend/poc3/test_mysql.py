from sqlmodel import select

from .database import get_session
from .logging_config import configure_logging
from .models import MaterialRecord


def main() -> None:
    configure_logging()
    with get_session() as session:
        records = session.exec(
            select(MaterialRecord).order_by(MaterialRecord.period)
        ).all()
        for record in records:
            print(record.sub_category, record.value)
        print(f"总计：{len(records)}")


if __name__ == "__main__":
    main()
