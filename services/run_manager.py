from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update
from db.database import AsyncSessionLocal
from db.models import ResearchRun
from schemas import RunStatus, ResearchStatusResponse, WriterOutput
from utils.logger import logger

class RunManager:
    """
    Manages the lifecycle and state persistence of ResearchRun records in PostgreSQL.
    """

    @staticmethod
    async def create_initial_run(run_id: str, question: str) -> None:
        """Inserts a new ResearchRun in PENDING status."""
        async with AsyncSessionLocal() as session:
            run = ResearchRun(
                run_id=run_id,
                question=question,
                status=RunStatus.PENDING.value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(run)
            await session.commit()
            logger.info(f"💾 [RunManager] Created initial run record for [cyan]{run_id}[/cyan]")

    @staticmethod
    async def update_status(
        run_id: str, status: RunStatus, error_message: Optional[str] = None
    ) -> None:
        """Updates the status of a run."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ResearchRun)
                .where(ResearchRun.run_id == run_id)
                .values(
                    status=status.value,
                    error_message=error_message,
                    updated_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def complete_run(
        run_id: str,
        report: Dict[str, Any],
        total_tokens: int,
        total_searches: int,
        revision_count: int,
        execution_time_sec: float,
    ) -> None:
        """Updates the run record with final report, statistics, and COMPLETED status."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ResearchRun)
                .where(ResearchRun.run_id == run_id)
                .values(
                    status=RunStatus.COMPLETED.value,
                    total_tokens=total_tokens,
                    total_searches=total_searches,
                    revision_count=revision_count,
                    execution_time_sec=execution_time_sec,
                    report_title=report.get("title"),
                    report_summary=report.get("summary"),
                    report_data=report,
                    citations=report.get("citations", []),
                    validation_warnings=report.get("validation_warnings", []),
                    updated_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"🎉 [RunManager] Saved completed report for [cyan]{run_id}[/cyan]")

    @staticmethod
    async def get_run_status(run_id: str) -> Optional[ResearchStatusResponse]:
        """Fetches run details and report by run_id."""
        async with AsyncSessionLocal() as session:
            stmt = select(ResearchRun).where(ResearchRun.run_id == run_id)
            result = await session.execute(stmt)
            run = result.scalar_one_or_none()
            if not run:
                return None

            writer_report = None
            if run.report_data:
                try:
                    writer_report = WriterOutput(**run.report_data)
                except Exception:
                    pass

            return ResearchStatusResponse(
                run_id=run.run_id,
                question=run.question,
                status=RunStatus(run.status),
                execution_time_sec=run.execution_time_sec or 0.0,
                total_tokens=run.total_tokens or 0,
                total_searches=run.total_searches or 0,
                revision_count=run.revision_count or 0,
                report=writer_report,
                error_message=run.error_message,
            )
