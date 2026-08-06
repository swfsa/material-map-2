"""Run GET /api/reports/latest against the configured MySQL database."""

from fastapi.testclient import TestClient

from poc4.main import app


def main() -> None:
    with TestClient(app) as client:
        response = client.get("/api/reports/latest")
        response.raise_for_status()

    payload = response.json()
    blocks = payload["report_ir"]["blocks"]
    print(f"GET /api/reports/latest status={response.status_code}")
    print(f"generated_at={payload['generated_at']}")
    print(f"blocks={len(blocks)}")
    print(f"block_types={','.join(block['type'] for block in blocks)}")
    print(f"html_chars={len(payload['html'])}")


if __name__ == "__main__":
    main()
