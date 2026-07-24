"""Configuring the task scheduler"""

from datetime import timezone
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.tasks.sync_jobs import (
    sync_ebiblio_job,
    sync_todostuslibros_job,
    sync_library_job,
)

logger = logging.getLogger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=timezone.utc)
    trigger = CronTrigger(hour=settings.SYNC_EXECUTION_HOUR, minute=0)

    scheduler.add_job(
        sync_ebiblio_job,
        trigger,
        id="sync_ebiblio",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=3600,
        max_instances=1,
    )
    scheduler.add_job(
        sync_todostuslibros_job,
        trigger,
        id="sync_todostuslibros",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=3600,
        max_instances=1,
    )
    scheduler.add_job(
        sync_library_job,
        trigger,
        id="sync_library",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=3600,
        max_instances=1,
    )

    logger.info("Scheduler configured for time %s (UTC)", settings.SYNC_EXECUTION_HOUR)
    return scheduler
