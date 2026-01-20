from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.utils import timezone

from home.tasks.recurring_task import run_recurring_task_job

scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)


def start_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        run_recurring_task_job,
        trigger=CronTrigger(hour=2, minute=0,timezone=timezone.get_current_timezone()),  # runs daily at 2:00 AM
        id="recurring_task_job",
        replace_existing=True,
    )

    scheduler.start()