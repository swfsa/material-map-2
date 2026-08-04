"""Run the GET /api/records chain against the configured MySQL database."""

import argparse

from fastapi.testclient import TestClient

from poc4.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category")
    parser.add_argument("--period-from")
    parser.add_argument("--period-to")
    args = parser.parse_args()

    params = {
        key: value
        for key, value in {
            "category": args.category,
            "period_from": args.period_from,
            "period_to": args.period_to,
        }.items()
        if value is not None
    }

    with TestClient(app) as client:
        response = client.get("/api/records", params=params)
        response.raise_for_status()

    records = response.json()
    print(f"GET /api/records status={response.status_code} records={len(records)}")
    if records:
        print(f"first_period={records[0]['period']} last_period={records[-1]['period']}")
        print(f"fields={','.join(records[0])}")


if __name__ == "__main__":
    main()
