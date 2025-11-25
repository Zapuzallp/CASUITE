from django.utils import timezone
from home.models import ClientService, Task
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)


def auto_generate_tasks():
    """
    Auto-generates recurring tasks for active client services.
    This function is designed to be idempotent and can be run daily.
    """
    today = timezone.now().date()
    active_services = ClientService.objects.filter(is_active=True, service__is_task=True).select_related('service',
                                                                                                         'client')

    for cs in active_services:
        service_type = cs.service
        frequency = service_type.frequency

        if frequency == 'One-time':
            continue

        last_task = Task.objects.filter(client_service=cs).order_by('-period_to').first()

        if last_task:
            # Start the next period on the day after the last period ended
            next_period_start = last_task.period_to + timedelta(days=1)
        else:
            # For the first task, use the service start date
            next_period_start = cs.start_date

        while next_period_start <= today:
            if frequency == 'Monthly':
                period_end = next_period_start + relativedelta(months=1) - timedelta(days=1)
                delta = relativedelta(months=1)
            elif frequency == 'Quarterly':
                period_end = next_period_start + relativedelta(months=3) - timedelta(days=1)
                delta = relativedelta(months=3)
            elif frequency == 'Yearly':
                period_end = next_period_start + relativedelta(years=1) - timedelta(days=1)
                delta = relativedelta(years=1)
            else:
                break  # Should not happen if frequency is validated

            # Ensure we don't create tasks for future periods
            if next_period_start > today:
                break

            # Check if a task for this period already exists
            # Use the actual next_period_start instead of forcing day=1 to maintain relative dates
            period_from = next_period_start
            task_exists = Task.objects.filter(
                client_service=cs,
                period_from=period_from,
                period_to=period_end
            ).exists()

            if not task_exists:
                due_date = period_end + timedelta(days=service_type.default_due_days)
                task_title = f"{service_type.service_name} - {period_from.strftime('%d %b %Y')} to {period_end.strftime('%d %b %Y')}"

                # Get the last task for this client service to copy the assigned_to field
                last_task = Task.objects.filter(client_service=cs).order_by('-id').first()
                assigned_to = last_task.assigned_to if last_task else None

                Task.objects.create(
                    client_service=cs,
                    task_title=task_title,
                    period_from=period_from,
                    period_to=period_end,
                    due_date=due_date,
                    task_status='Pending',
                    recurrence=frequency,
                    assigned_to=assigned_to,  # Copy from previous task if exists
                )
                logger.info(f"Auto-generated task: '{task_title}' for client '{cs.client.client_name}'")

            # Move to the next period by setting the next period start to the day after the current period ends
            next_period_start = period_end + timedelta(days=1)

            # If we're at the end of the current period, ensure we don't get stuck in an infinite loop
            if next_period_start > today:
                break
