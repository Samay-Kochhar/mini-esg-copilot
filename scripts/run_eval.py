from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import init_db
from app.main import app


async def wait_for_done(client: AsyncClient, report_id: int, max_retries: int = 30) -> dict:
    for _ in range(max_retries):
        res = await client.get(f"/reports/{report_id}/strategy")
        if res.status_code == 404:
            await asyncio.sleep(0.05)
            continue
        data = res.json()
        if data["status"] in {"done", "failed"}:
            return data
        await asyncio.sleep(0.05)
    raise RuntimeError(f"Timed out waiting for strategy generation for report {report_id}.")


def _contains_required_numbers(strategy_text: str, expected: list[str]) -> bool:
    return all(num in strategy_text for num in expected)


async def run_eval() -> None:
    await init_db()
    cases_path = PROJECT_ROOT / "tests" / "eval_cases.json"
    cases = json.loads(cases_path.read_text())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        passed = 0
        for case in cases:
            report_res = await client.post("/reports", json=case["payload"])
            report_res.raise_for_status()
            report = report_res.json()
            report_id = report["id"]

            gen_res = await client.post(f"/reports/{report_id}/generate-strategy")
            gen_res.raise_for_status()

            strategy_obj = await wait_for_done(client, report_id)
            has_variants = (
                strategy_obj["status"] == "done"
                and strategy_obj.get("strategy")
                and {"short", "neutral", "detailed"}.issubset(strategy_obj["strategy"].keys())
            )

            expected_numbers = [
                str(report["reporting_year"]),
                str(report["scope1_tco2e"]),
                str(report["scope2_tco2e"]),
            ]
            texts = [
                strategy_obj.get("strategy", {}).get("short", ""),
                strategy_obj.get("strategy", {}).get("neutral", ""),
                strategy_obj.get("strategy", {}).get("detailed", ""),
            ]
            numbers_ok = all(_contains_required_numbers(text, expected_numbers) for text in texts)

            guardrails = strategy_obj.get("guardrail_result", {})
            guardrails_ok = all(
                guardrails.get(name, {}).get("status") in {"pass", "warn"}
                for name in ("short", "neutral", "detailed")
            )

            case_ok = bool(has_variants and numbers_ok and guardrails_ok)
            passed += int(case_ok)
            print(
                f"[{case['name']}] status={strategy_obj['status']} variants={has_variants} "
                f"numbers={numbers_ok} guardrails={guardrails_ok} result={'PASS' if case_ok else 'FAIL'}"
            )

        print(f"\nSummary: {passed}/{len(cases)} cases passed.")


if __name__ == "__main__":
    asyncio.run(run_eval())
