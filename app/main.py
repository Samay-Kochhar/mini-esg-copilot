from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_db, init_db
from app.models import Report, StrategyGeneration, StrategyStatus, UnitEnum
from app.schemas import ReportCreate, ReportOut, StrategyGenerationOut, StrategyPayload
from app.services.guardrails import run_guardrails
from app.services.normalization import round_value, to_tco2e
from app.services.strategy_generator import generate_strategy_payload
from app.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Mini AI ESG Copilot Pipeline",
    version="0.1.0",
    lifespan=lifespan,
)


def _ui_file_path() -> Path:
    return Path(__file__).resolve().parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
async def ui_index() -> FileResponse:
    return FileResponse(_ui_file_path())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _serialize_generation(
    generation: StrategyGeneration, report_id: int
) -> StrategyGenerationOut:
    strategy_payload = None
    if generation.short_text and generation.neutral_text and generation.detailed_text:
        strategy_payload = StrategyPayload(
            short=generation.short_text,
            neutral=generation.neutral_text,
            detailed=generation.detailed_text,
            numbers_used=generation.numbers_used or {},
        )

    return StrategyGenerationOut(
        report_id=report_id,
        status=generation.status.value,
        strategy=strategy_payload,
        guardrail_result=generation.guardrail_result,
        model_name=generation.model_name,
        prompt_version=generation.prompt_version,
        duration_ms=generation.duration_ms,
        token_usage=generation.token_usage,
        error_message=generation.error_message,
        created_at=generation.created_at,
        updated_at=generation.updated_at,
    )


async def _run_generation_job(report_id: int) -> None:
    start = time.perf_counter()
    async with SessionLocal() as session:
        try:
            report = await session.get(Report, report_id)
            if report is None:
                return

            stmt = select(StrategyGeneration).where(StrategyGeneration.report_id == report_id)
            result = await session.execute(stmt)
            generation = result.scalar_one_or_none()
            if generation is None or generation.status != StrategyStatus.PENDING:
                return

            payload = await asyncio.wait_for(
                generate_strategy_payload(
                    company_name=report.company_name,
                    reporting_year=report.reporting_year,
                    scope1_tco2e=round_value(report.scope1_tco2e),
                    scope2_tco2e=round_value(report.scope2_tco2e),
                    notes=report.notes,
                ),
                timeout=settings.generation_timeout_seconds,
            )
            guardrails = run_guardrails(
                payload,
                reporting_year=report.reporting_year,
                scope1_tco2e=round_value(report.scope1_tco2e),
                scope2_tco2e=round_value(report.scope2_tco2e),
            )

            generation.short_text = payload.short
            generation.neutral_text = payload.neutral
            generation.detailed_text = payload.detailed
            generation.numbers_used = payload.numbers_used.model_dump(mode="json")
            generation.guardrail_result = guardrails.model_dump(mode="json")
            generation.status = StrategyStatus.DONE
            generation.duration_ms = int((time.perf_counter() - start) * 1000)
            generation.error_message = None
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            stmt = select(StrategyGeneration).where(StrategyGeneration.report_id == report_id)
            result = await session.execute(stmt)
            generation = result.scalar_one_or_none()
            if generation is None:
                return
            generation.status = StrategyStatus.FAILED
            generation.duration_ms = int((time.perf_counter() - start) * 1000)
            generation.error_message = str(exc)[:380]
            await session.commit()


@app.post("/reports", response_model=ReportOut, status_code=201)
async def create_report(
    payload: ReportCreate, db: AsyncSession = Depends(get_db)
) -> ReportOut:
    report = Report(
        company_name=payload.company_name.strip(),
        reporting_year=payload.reporting_year,
        scope1_value=round_value(payload.scope1_value),
        scope1_unit=UnitEnum(payload.scope1_unit.value),
        scope1_tco2e=to_tco2e(payload.scope1_value, payload.scope1_unit),
        scope2_value=round_value(payload.scope2_value),
        scope2_unit=UnitEnum(payload.scope2_unit.value),
        scope2_tco2e=to_tco2e(payload.scope2_value, payload.scope2_unit),
        scope3_value=round_value(payload.scope3_value) if payload.scope3_value else None,
        scope3_unit=UnitEnum(payload.scope3_unit.value) if payload.scope3_unit else None,
        scope3_tco2e=(
            to_tco2e(payload.scope3_value, payload.scope3_unit)
            if payload.scope3_value and payload.scope3_unit
            else None
        ),
        energy_consumption_kwh=(
            round_value(payload.energy_consumption_kwh)
            if payload.energy_consumption_kwh is not None
            else None
        ),
        notes=payload.notes,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return ReportOut.model_validate(report)


@app.get("/reports/latest", response_model=ReportOut)
async def get_latest_report(db: AsyncSession = Depends(get_db)) -> ReportOut:
    stmt = select(Report).order_by(Report.created_at.desc(), Report.id.desc()).limit(1)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="No reports saved yet.")
    return ReportOut.model_validate(report)


@app.post("/reports/{report_id}/generate-strategy", response_model=StrategyGenerationOut)
async def generate_strategy(
    report_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> StrategyGenerationOut:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")

    stmt = select(StrategyGeneration).where(StrategyGeneration.report_id == report_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return _serialize_generation(existing, report_id)

    generation = StrategyGeneration(
        report_id=report_id,
        status=StrategyStatus.PENDING,
        model_name=settings.model_name,
        prompt_version=settings.prompt_version,
    )
    db.add(generation)
    try:
        await db.commit()
        await db.refresh(generation)
    except IntegrityError:
        await db.rollback()
        result = await db.execute(stmt)
        generation = result.scalar_one()
        return _serialize_generation(generation, report_id)

    background_tasks.add_task(_run_generation_job, report_id)
    return _serialize_generation(generation, report_id)


@app.get("/reports/{report_id}/strategy", response_model=StrategyGenerationOut)
async def get_strategy(
    report_id: int, db: AsyncSession = Depends(get_db)
) -> StrategyGenerationOut:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")

    stmt = select(StrategyGeneration).where(StrategyGeneration.report_id == report_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()
    if generation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy for report {report_id} has not been generated yet.",
        )
    return _serialize_generation(generation, report_id)
