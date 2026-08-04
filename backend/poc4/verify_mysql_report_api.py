"""Run GET /api/ReportIR against the configured MySQL database."""

from fastapi.testclient import TestClient

from poc4.main import app


def main() -> None:
    with TestClient(app) as client:
        response = client.get("/api/ReportIR")
        response.raise_for_status()

    report = response.json()
    evidence = report["evidence"]
    print(f"GET /api/ReportIR status={response.status_code}")
    print(f"title={report['title']}")
    print(f"fields={','.join(report)}")
    print(
        "evidence="
        f"internal:{len(evidence['internal'])},"
        f"external:{len(evidence['external'])}"
    )


if __name__ == "__main__":
    main()
