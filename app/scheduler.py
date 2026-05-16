"""
APKDroid Background Scheduler.
Runs the daily scrape pipeline at 3 AM UTC every day.
Creates a fresh DB session per job — never shares a session across jobs.
"""

import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _run_daily_sync():
    """
    Wrapper called by APScheduler (sync context).
    Creates its own DB session and event loop so it is fully self-contained.
    """
    from app.database import SessionLocal
    from app.services.legal_scraper import run_daily_sync

    db = SessionLocal()
    try:
        logger.info("APScheduler: daily sync starting...")
        # APScheduler runs in a thread, so we need a fresh event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_daily_sync(db))
        loop.close()
        logger.info(f"APScheduler: daily sync complete — {results}")
    except Exception as e:
        logger.error(f"APScheduler: daily sync FAILED — {e}", exc_info=True)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    """
    Start the background scheduler.
    Schedules:
      • 3:00 AM UTC daily — full scrape (50 apps/OS) + description generation
    """
    scheduler = BackgroundScheduler(daemon=True)

    scheduler.add_job(
        func=_run_daily_sync,
        trigger=CronTrigger(hour=3, minute=0, second=0, timezone="UTC"),
        id="daily_app_sync",
        name="Daily App Scrape + Description Generation (50/OS)",
        replace_existing=True,
        misfire_grace_time=3600,   # allow up to 1h late start
        coalesce=True,             # skip missed runs
    )

    try:
        scheduler.start()
        next_run = scheduler.get_job("daily_app_sync").next_run_time
        logger.info(f"✅ Scheduler started — next run: {next_run} UTC")
    except Exception as e:
        logger.error(f"❌ Scheduler failed to start: {e}")
        return None

    return scheduler
