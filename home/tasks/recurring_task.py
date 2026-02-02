from django.utils import timezone
from django.db import transaction
from home.models import Task,TaskRecurrence
from home.scheduler.recurrence import get_next_recurrence_date
from .task_copy import copy_task

def run_recurring_task_job():
    """
    Scheduler job:
    - Scan TaskRecurrence only
    - Use next_run_at as source of truth
    - Create ALL missed recurring tasks
    - Advance next_run_at deterministically
    """
    now = timezone.now()

    recurrences = (
        TaskRecurrence.objects
        .filter(
            is_recurring=True,
            next_run_at__isnull=False,
            next_run_at__lte=now,
        )
        .select_related("task")
    )

    for recurrence in recurrences:
        with transaction.atomic():

            while recurrence.next_run_at <= now:

                # 1️.Create task for this expected occurrence
                copy_task(
                    recurrence.task,
                    is_auto=True,
                    next_due_date=recurrence.next_run_at,
                )

                # 2️.Track actual creation timestamp
                created_at = timezone.now()
                recurrence.last_auto_created_at = created_at
                recurrence.task.last_auto_created_at = created_at


                # 3️.Move EXPECTED schedule forward
                recurrence.next_run_at = get_next_recurrence_date(recurrence)
            # 4️.Persist once per recurrence
            recurrence.save(update_fields=[
                "last_auto_created_at",
                "next_run_at",
            ])
            recurrence.task.save(update_fields=[
                "last_auto_created_at",
            ])