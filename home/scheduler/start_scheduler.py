from django_apscheduler.jobstores import DjangoJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.utils import timezone
import logging

from home.tasks.recurring_task import run_recurring_task_job

logger = logging.getLogger(__name__)

# Initialize scheduler with Django job store
scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
scheduler.add_jobstore(DjangoJobStore(), "default")


def start_scheduler():
    """
    Start the APScheduler background scheduler.
    Jobs are stored in Django database for persistence and visibility.
    """
    if scheduler.running:
        logger.info("Scheduler is already running")
        return

    try:
        # Add recurring task job - runs daily at 2:00 AM
        scheduler.add_job(
            run_recurring_task_job,
            trigger=CronTrigger(
                hour=2,
                minute=0,
                timezone=timezone.get_current_timezone()
            ),
            id="recurring_task_job",
            name="Auto-create Recurring Tasks",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent execution
            misfire_grace_time=3600,  # Allow 1 hour grace period for missed jobs
        )

        scheduler.start()
        logger.info("Scheduler started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        raise


def stop_scheduler():
    """
    Stop the scheduler gracefully.
    """
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped successfully")
    else:
        logger.info("Scheduler is not running")