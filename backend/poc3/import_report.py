"""把已有的 ReportIR JSON 文件幂等导入数据库。"""

import argparse
import json
from pathlib import Path

from .database import create_report_table, get_session
from .report import LegacyReportIR, validate_stored_report
from .repository import ReportRepository


def import_report(path: Path) -> tuple[int, bool]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("ReportIR 文件顶层必须是 JSON 对象")
    report = validate_stored_report(payload)
    legacy = LegacyReportIR.model_validate(payload) if "blocks" not in payload else None
    create_report_table()

    with get_session() as session:
        row, created = ReportRepository(session).save(
            report,
            data_window_start=legacy.data_window.start if legacy else None,
            data_window_end=legacy.data_window.end if legacy else None,
        )
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
