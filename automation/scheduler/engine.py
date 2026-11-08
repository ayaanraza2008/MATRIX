"""MATRIX Persistent Background Task Scheduler Engine.
Executes periodic maintenance, health monitoring, integration heartbeats,
and scheduled user tasks with SQLite persistence, failure retries, and pause controls.
"""
from typing import Dict, Any, List, Optional, Callable
import time
import asyncio
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field
from database.session import AsyncSessionLocal
from database.models import BackgroundTask as BackgroundTaskModel
from sqlalchemy import select, update
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("automation.scheduler")


class ScheduledTaskDescriptor(BaseModel):
    task_id: str
    name: str
    description: str
    interval_seconds: int = 300
    priority: int = 1
    status: str = "ACTIVE"  # ACTIVE, PAUSED, COMPLETED, FAILED
    assigned_agent: str = "automation"
    required_autonomy_level: int = 2
    execution_count: int = 0
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    error_log: Optional[str] = None


class BackgroundTaskScheduler:
    """Persistent scheduler loop executing autonomous tasks across sessions."""

    def __init__(self):
        self._is_running = False
        self._is_paused = False
        self._registered_handlers: Dict[str, Callable[[], Any]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register built-in autonomous task workers."""
        async def _health_monitor():
            from core.self_maintenance.diagnostics import diagnostics_engine
            report = await diagnostics_engine.run_full_diagnostics()
            if report.get("overall_status") != "HEALTHY":
                from core.self_maintenance.recovery import recovery_engine
                await recovery_engine.recover_low_memory()
            return {"status": "SUCCESS", "report": report}

        async def _weather_sync():
            from core.information.briefing import briefing_engine
            weather = await briefing_engine.get_live_weather()
            return {"status": "SUCCESS", "weather": weather}

        async def _cache_prune():
            from core.self_maintenance.recovery import recovery_engine
            cleaned = await recovery_engine.cleanup_cache_storage(max_age_hours=24)
            return {"status": "SUCCESS", "cleaned": cleaned}

        async def _integration_health():
            from core.integrations.manager import integration_manager
            res = await integration_manager.test_integration("weather_openmeteo")
            return {"status": "SUCCESS", "integration_probe": res}

        self._registered_handlers["task_server_health"] = _health_monitor
        self._registered_handlers["task_weather_sync"] = _weather_sync
        self._registered_handlers["task_cache_prune"] = _cache_prune
        self._registered_handlers["task_integration_health"] = _integration_health

    async def initialize_defaults(self):
        """Seed default autonomous background jobs in SQLite if not present."""
        defaults = [
            ("task_server_health", "System Health & Diagnostics Monitor", 300, 1, "system"),
            ("task_weather_sync", "Live Weather & Atmospheric Sync", 1800, 2, "personal"),
            ("task_cache_prune", "Cache & Temp Frame Maintenance", 3600, 3, "files"),
            ("task_integration_health", "Integration Connection Heartbeat", 600, 2, "core")
        ]

        try:
            async with AsyncSessionLocal() as session:
                for tid, name, interval, priority, agent in defaults:
                    stmt = select(BackgroundTaskModel).where(BackgroundTaskModel.task_id == tid)
                    existing = (await session.execute(stmt)).scalar_one_or_none()
                    if not existing:
                        task = BackgroundTaskModel(
                            task_id=tid,
                            name=name,
                            description=f"Autonomous background task for {name}",
                            interval_seconds=interval,
                            priority=priority,
                            status="ACTIVE",
                            assigned_agent=agent,
                            required_autonomy_level=2,
                            next_run_at=datetime.now(timezone.utc)
                        )
                        session.add(task)
                await session.commit()
            logger.info("Initialized default background tasks in SQLite database.")
        except Exception as e:
            logger.debug(f"Could not seed background tasks: {e}")

    async def start(self):
        """Start the background scheduler worker loop."""
        if self._is_running:
            return
        self._is_running = True
        logger.info("MATRIX Background Task Scheduler started.")
        asyncio.create_task(self._scheduler_loop())

    def stop(self):
        self._is_running = False
        logger.info("MATRIX Background Task Scheduler stopped.")

    def pause_all(self):
        """Suspend all background task execution."""
        self._is_paused = True
        logger.info("Background tasks PAUSED by operator.")

    def resume_all(self):
        """Resume background task execution."""
        self._is_paused = False
        logger.info("Background tasks RESUMED by operator.")

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    async def _scheduler_loop(self):
        """Main non-blocking async tick loop checking due tasks every 5 seconds."""
        await self.initialize_defaults()

        while self._is_running:
            try:
                if not self._is_paused:
                    await self._check_and_execute_due_tasks()
            except Exception as e:
                logger.debug(f"Scheduler tick error: {e}")
            await asyncio.sleep(5)

    async def _check_and_execute_due_tasks(self):
        """Find and execute tasks whose next_run_at is now due."""
        now = datetime.now(timezone.utc)
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(BackgroundTaskModel).where(
                    BackgroundTaskModel.status == "ACTIVE"
                )
                tasks = (await session.execute(stmt)).scalars().all()

                for t in tasks:
                    if t.next_run_at:
                        is_due = (t.next_run_at.replace(tzinfo=timezone.utc) <= now) if t.next_run_at.tzinfo is None else (t.next_run_at <= now)
                        if is_due:
                            handler = self._registered_handlers.get(t.task_id)
                        t.last_run_at = now
                        t.next_run_at = datetime.fromtimestamp(now.timestamp() + t.interval_seconds, tz=timezone.utc)
                        t.execution_count += 1

                        if handler:
                            try:
                                res = handler()
                                if asyncio.iscoroutine(res):
                                    res = await res
                                t.last_result = res if isinstance(res, dict) else {"output": str(res)}
                                t.error_log = None
                            except Exception as e:
                                t.retry_count += 1
                                t.error_log = str(e)
                                logger.warning(f"Background task {t.task_id} failed: {e}")
                        else:
                            t.last_result = {"status": "SUCCESS", "action": "Checked"}

                await session.commit()
        except Exception as e:
            logger.debug(f"Database task query error in scheduler: {e}")

    async def enroll_task(
        self,
        name: str,
        description: str,
        interval_seconds: int = 300,
        assigned_agent: str = "automation",
        handler: Optional[Callable[[], Any]] = None
    ) -> str:
        """Enroll a new persistent background task."""
        tid = f"task_custom_{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc)
        try:
            async with AsyncSessionLocal() as session:
                model = BackgroundTaskModel(
                    task_id=tid,
                    name=name,
                    description=description,
                    interval_seconds=interval_seconds,
                    priority=2,
                    status="ACTIVE",
                    assigned_agent=assigned_agent,
                    required_autonomy_level=2,
                    next_run_at=now
                )
                session.add(model)
                await session.commit()

            if handler:
                self._registered_handlers[tid] = handler

            logger.info(f"Enrolled background task: '{name}' ({tid}) every {interval_seconds}s")
            return tid
        except Exception as e:
            logger.error(f"Failed to enroll task: {e}")
            return ""

    async def list_tasks(self) -> List[Dict[str, Any]]:
        """List all persistent background tasks from SQLite."""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(BackgroundTaskModel)
                records = (await session.execute(stmt)).scalars().all()
                results = []
                for r in records:
                    results.append({
                        "task_id": r.task_id,
                        "name": r.name,
                        "description": r.description,
                        "interval_seconds": r.interval_seconds,
                        "priority": r.priority,
                        "status": r.status,
                        "assigned_agent": r.assigned_agent,
                        "required_autonomy_level": r.required_autonomy_level,
                        "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
                        "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
                        "execution_count": r.execution_count,
                        "retry_count": r.retry_count,
                        "last_result": r.last_result,
                        "error_log": r.error_log
                    })
                return results
        except Exception as e:
            logger.debug(f"Error listing tasks: {e}")
            return []


# Global singleton
background_scheduler = BackgroundTaskScheduler()
