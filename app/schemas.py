from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UnitIn(StrEnum):
    KG_CO2E = "kg_co2e"
    T_CO2E = "t_co2e"


class StrategyStatusOut(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1, max_length=255)
    reporting_year: int = Field(ge=1900, le=2200)

    scope1_value: Decimal = Field(gt=0)
    scope1_unit: UnitIn
    scope2_value: Decimal = Field(gt=0)
    scope2_unit: UnitIn

    scope3_value: Decimal | None = Field(default=None, gt=0)
    scope3_unit: UnitIn | None = None
    energy_consumption_kwh: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("reporting_year", mode="before")
    @classmethod
    def validate_reporting_year_type(cls, value: object) -> object:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("reporting_year must be an integer.")
        return value

    @field_validator(
        "scope1_value",
        "scope2_value",
        "scope3_value",
        "energy_consumption_kwh",
        mode="before",
    )
    @classmethod
    def validate_number_fields(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("This field must be a number.")
        return Decimal(str(value))

    @model_validator(mode="after")
    def validate_scope3_pair(self) -> "ReportCreate":
        if (self.scope3_value is None) != (self.scope3_unit is None):
            raise ValueError(
                "scope3_value and scope3_unit must be provided together."
            )
        return self


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    reporting_year: int
    scope1_value: Decimal
    scope1_unit: UnitIn
    scope1_tco2e: Decimal
    scope2_value: Decimal
    scope2_unit: UnitIn
    scope2_tco2e: Decimal
    scope3_value: Decimal | None = None
    scope3_unit: UnitIn | None = None
    scope3_tco2e: Decimal | None = None
    energy_consumption_kwh: Decimal | None = None
    notes: str | None = None
    created_at: datetime


class StrategyNumbersUsed(BaseModel):
    model_config = ConfigDict()

    reporting_year: int
    scope1_tco2e: Decimal
    scope2_tco2e: Decimal


class StrategyPayload(BaseModel):
    model_config = ConfigDict()

    short: str
    neutral: str
    detailed: str
    numbers_used: StrategyNumbersUsed


class VariantGuardrail(BaseModel):
    model_config = ConfigDict()

    status: str
    reasons: list[str]


class GuardrailResult(BaseModel):
    model_config = ConfigDict()

    short: VariantGuardrail
    neutral: VariantGuardrail
    detailed: VariantGuardrail


class StrategyGenerationOut(BaseModel):
    model_config = ConfigDict()

    report_id: int
    status: StrategyStatusOut
    strategy: StrategyPayload | None = None
    guardrail_result: GuardrailResult | None = None
    model_name: str
    prompt_version: str
    duration_ms: int | None = None
    token_usage: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
