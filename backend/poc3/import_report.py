"""把已有的 ReportIR JSON 文件幂等导入数据库。"""

import argparse
import json
from pathlib import Path

from .database import create_report_table, get_session
from .report import ReportIR
from .repository import ReportRepository


def import_report(path: Path) -> tuple[int, bool]:
    report = ReportIR.model_validate_json(path.read_text(encoding="utf-8-sig"))
    create_report_table()

    with get_session() as session:
        row, created = ReportRepository(session).save(report)
        session.commit()
        session.refresh(row)
        if row.id is None:
            raise RuntimeError("ReportIR 保存后未生成数据库主键")
        return row.id, created


def main() -> None:
    parser = argparse.ArgumentParser(description="导入一份 ReportIR JSON")
    parser.add_argument("path", type=Path, help="ReportIR JSON 文件路径")
    args = parser.parse_args()

    report_id, created = import_report(args.path)
    print(
        json.dumps(
            {
                "report_id": report_id,
                "status": "created" if created else "already_exists",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
