from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UnitEnum(StrEnum):
    KG_CO2E = "kg_co2e"
    T_CO2E = "t_co2e"


class StrategyStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False)

    scope1_value: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    scope1_unit: Mapped[UnitEnum] = mapped_column(Enum(UnitEnum), nullable=False)
    scope1_tco2e: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)

    scope2_value: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    scope2_unit: Mapped[UnitEnum] = mapped_column(Enum(UnitEnum), nullable=False)
    scope2_tco2e: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)

    scope3_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
    scope3_unit: Mapped[UnitEnum | None] = mapped_column(Enum(UnitEnum), nullable=True)
    scope3_tco2e: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)

    energy_consumption_kwh: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    strategy_generation: Mapped["StrategyGeneration | None"] = relationship(
        "StrategyGeneration",
        back_populates="report",
        uselist=False,
        cascade="all, delete-orphan",
    )


class StrategyGeneration(Base):
    __tablename__ = "strategy_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[StrategyStatus] = mapped_column(
        Enum(StrategyStatus), nullable=False, default=StrategyStatus.PENDING
    )
    short_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    neutral_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    detailed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    numbers_used: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    guardrail_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    model_name: Mapped[str] = mapped_column(String(120), nullable=False, default="stub")
    prompt_version: Mapped[str] = mapped_column(
        String(60), nullable=False, default="stub_v1"
    )
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    report: Mapped[Report] = relationship("Report", back_populates="strategy_generation")

