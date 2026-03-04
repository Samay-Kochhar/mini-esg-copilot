from __future__ import annotations

import re
from decimal import Decimal

from app.schemas import GuardrailResult, StrategyPayload, VariantGuardrail
from app.services.normalization import round_value

NUMBER_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
STRUCTURAL_NUMBER_CONTEXT_RE = re.compile(
    r"(scope|action\s+block|block|step)\s*$", re.IGNORECASE
)


def _build_variant_result(reasons: list[str]) -> VariantGuardrail:
    if not reasons:
        return VariantGuardrail(status="pass", reasons=[])
    if len(reasons) == 1:
        return VariantGuardrail(status="warn", reasons=reasons)
    return VariantGuardrail(status="fail", reasons=reasons)


def _check_number_consistency(
    payload: StrategyPayload,
    reporting_year: int,
    scope1_tco2e: Decimal,
    scope2_tco2e: Decimal,
) -> list[str]:
    reasons: list[str] = []
    if payload.numbers_used.reporting_year != reporting_year:
        reasons.append("numbers_used.reporting_year does not match stored value.")
    if round_value(payload.numbers_used.scope1_tco2e) != round_value(scope1_tco2e):
        reasons.append("numbers_used.scope1_tco2e does not match stored normalized value.")
    if round_value(payload.numbers_used.scope2_tco2e) != round_value(scope2_tco2e):
        reasons.append("numbers_used.scope2_tco2e does not match stored normalized value.")
    return reasons


def _check_unit_consistency(text: str) -> list[str]:
    reasons: list[str] = []
    lower = text.lower()
    if "kg" in lower and "tco2e" in lower:
        reasons.append("Text mixes kg and tCO2e without clear conversion explanation.")
    if "co2e" in lower and "tco2e" not in lower and "kg_co2e" not in lower:
        reasons.append("Unit reference is unclear. Use explicit tCO2e wording.")
    return reasons


def _check_hallucination_risk(text: str, allowed_numbers: set[str]) -> list[str]:
    reasons: list[str] = []
    extra_numbers: list[str] = []
    for match in NUMBER_TOKEN_RE.finditer(text):
        num = match.group(0)
        if num in allowed_numbers:
            continue

        # Ignore structural labels like "Scope 1" or "Action Block 3".
        prefix = text[max(0, match.start() - 24) : match.start()]
        if STRUCTURAL_NUMBER_CONTEXT_RE.search(prefix):
            continue

        extra_numbers.append(num)
    if extra_numbers:
        reasons.append(
            "Text includes extra numeric claims not present in inputs or normalized values."
        )
    return reasons


def run_guardrails(
    payload: StrategyPayload,
    *,
    reporting_year: int,
    scope1_tco2e: Decimal,
    scope2_tco2e: Decimal,
) -> GuardrailResult:
    base_numeric_reasons = _check_number_consistency(
        payload, reporting_year, scope1_tco2e, scope2_tco2e
    )
    allowed_numbers = {
        str(reporting_year),
        str(round_value(scope1_tco2e)),
        str(round_value(scope2_tco2e)),
        str(round_value(scope1_tco2e + scope2_tco2e)),
    }

    short_reasons = [
        *base_numeric_reasons,
        *_check_unit_consistency(payload.short),
        *_check_hallucination_risk(payload.short, allowed_numbers),
    ]
    neutral_reasons = [
        *base_numeric_reasons,
        *_check_unit_consistency(payload.neutral),
        *_check_hallucination_risk(payload.neutral, allowed_numbers),
    ]
    detailed_reasons = [
        *base_numeric_reasons,
        *_check_unit_consistency(payload.detailed),
        *_check_hallucination_risk(payload.detailed, allowed_numbers),
    ]

    return GuardrailResult(
        short=_build_variant_result(short_reasons),
        neutral=_build_variant_result(neutral_reasons),
        detailed=_build_variant_result(detailed_reasons),
    )
