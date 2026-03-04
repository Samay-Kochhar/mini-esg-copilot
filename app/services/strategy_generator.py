from __future__ import annotations

from decimal import Decimal

from app.schemas import StrategyNumbersUsed, StrategyPayload
from app.services.normalization import round_value


def _impact_band(scope1_tco2e: Decimal, scope2_tco2e: Decimal) -> str:
    total = scope1_tco2e + scope2_tco2e
    if total >= Decimal("100000"):
        return "high"
    if total >= Decimal("10000"):
        return "medium"
    return "low"


async def generate_strategy_payload(
    *,
    company_name: str,
    reporting_year: int,
    scope1_tco2e: Decimal,
    scope2_tco2e: Decimal,
    notes: str | None,
) -> StrategyPayload:
    scope1_text = f"{round_value(scope1_tco2e)} tCO2e"
    scope2_text = f"{round_value(scope2_tco2e)} tCO2e"
    total = round_value(scope1_tco2e + scope2_tco2e)
    band = _impact_band(scope1_tco2e, scope2_tco2e)
    note_line = (
        f" Notes context: {notes.strip()[:140]}."
        if notes and notes.strip()
        else ""
    )

    short = (
        f"For {reporting_year}, {company_name} reports Scope 1 at {scope1_text} and Scope 2 at {scope2_text}. "
        f"Combined emissions are {total} tCO2e, so this is a {band}-impact baseline. "
        "First priority is reducing operational energy loss and purchased-power intensity."
    )

    neutral = (
        f"In {reporting_year}, {company_name} has Scope 1 emissions of {scope1_text} and Scope 2 emissions of {scope2_text}. "
        f"The combined baseline is {total} tCO2e and falls in a {band}-impact profile. "
        "Start with an early audit to find top emission drivers in fuel usage and purchased electricity. "
        "Set ownership at plant and procurement levels so monthly actions are accountable. "
        "Run a quick-win package: maintenance optimization, process tuning, and supplier energy clauses. "
        "Then move to medium-term actions: contract power changes and equipment upgrades. "
        "Track progress with one dashboard that reports Scope 1 and Scope 2 monthly. "
        f"Use the {reporting_year} baseline to measure each quarter's reduction trend.{note_line}"
    )

    detailed = (
        f"Baseline ({reporting_year}): Scope 1 = {scope1_text}; Scope 2 = {scope2_text}; Total = {total} tCO2e.\n"
        "Action Block 1 - Measure and control: Map top emission sources, lock monthly reporting, and assign owners.\n"
        "Action Block 2 - Quick reductions: Cut avoidable fuel use, optimize operations, and reduce purchased-power waste.\n"
        "Action Block 3 - Structural moves: Upgrade high-impact assets and shift electricity contracts toward lower-emission supply.\n"
        "Action Block 4 - Governance: Link plant KPIs, procurement KPIs, and leadership review cadence to Scope 1 and Scope 2 outcomes.\n"
        "Action Block 5 - Evidence and traceability: Keep an auditable monthly trail from source data to reported tCO2e values."
    )

    return StrategyPayload(
        short=short,
        neutral=neutral,
        detailed=detailed,
        numbers_used=StrategyNumbersUsed(
            reporting_year=reporting_year,
            scope1_tco2e=round_value(scope1_tco2e),
            scope2_tco2e=round_value(scope2_tco2e),
        ),
    )
