from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

# Use isolated DB file for tests before importing app modules.
TEST_DB_PATH = Path(__file__).resolve().parent / "test_esg_copilot.db"
os.environ["ESG_DB_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import StrategyGeneration  # noqa: E402


def _reset_db() -> None:
    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_run())


@pytest.fixture(autouse=True)
def reset_db_fixture() -> None:
    _reset_db()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_create_report_and_get_latest(client: TestClient) -> None:
    payload = {
        "company_name": "Acme ESG Ltd",
        "reporting_year": 2024,
        "scope1_value": 120000,
        "scope1_unit": "kg_co2e",
        "scope2_value": 33.3,
        "scope2_unit": "t_co2e",
        "notes": "Demo note",
    }
    create_res = client.post("/reports", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["scope1_tco2e"] == "120.000"
    assert created["scope2_tco2e"] == "33.300"

    latest_res = client.get("/reports/latest")
    assert latest_res.status_code == 200
    latest = latest_res.json()
    assert latest["id"] == created["id"]
    assert latest["company_name"] == "Acme ESG Ltd"


def test_validation_rejects_string_numbers(client: TestClient) -> None:
    payload = {
        "company_name": "Strict Type Inc",
        "reporting_year": 2024,
        "scope1_value": "120000",
        "scope1_unit": "kg_co2e",
        "scope2_value": 10,
        "scope2_unit": "t_co2e",
    }
    res = client.post("/reports", json=payload)
    assert res.status_code == 422
    body = res.json()
    assert "detail" in body


def test_generate_strategy_idempotent_and_retrievable(client: TestClient) -> None:
    payload = {
        "company_name": "Idempotent Co",
        "reporting_year": 2025,
        "scope1_value": 50000,
        "scope1_unit": "kg_co2e",
        "scope2_value": 30000,
        "scope2_unit": "kg_co2e",
    }
    report = client.post("/reports", json=payload).json()
    report_id = report["id"]

    first = client.post(f"/reports/{report_id}/generate-strategy")
    assert first.status_code == 200

    second = client.post(f"/reports/{report_id}/generate-strategy")
    assert second.status_code == 200
    assert second.json()["created_at"] == first.json()["created_at"]

    strategy = None
    for _ in range(20):
        fetch = client.get(f"/reports/{report_id}/strategy")
        assert fetch.status_code == 200
        strategy = fetch.json()
        if strategy["status"] == "done":
            break
        asyncio.run(asyncio.sleep(0.05))

    assert strategy is not None
    assert strategy["status"] == "done"
    assert set(strategy["strategy"].keys()) == {
        "short",
        "neutral",
        "detailed",
        "numbers_used",
    }
    assert strategy["strategy"]["numbers_used"]["reporting_year"] == 2025

    async def _count_rows() -> int:
        async with SessionLocal() as session:
            result = await session.execute(
                select(StrategyGeneration).where(StrategyGeneration.report_id == report_id)
            )
            rows = result.scalars().all()
            return len(rows)

    assert asyncio.run(_count_rows()) == 1

