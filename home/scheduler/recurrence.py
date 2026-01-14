from datetime import date
from dateutil.relativedelta import relativedelta
import calendar


def is_last_day_of_month(dt):
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return dt.day == last_day


def add_months_safe(base_date, months):
    """
    Adds months while safely handling end-of-month cases.
    """
    target = base_date + relativedelta(months=months)

    # If original date was last day of month,
    # force result to last day of target month
    if is_last_day_of_month(base_date):
        last_day = calendar.monthrange(target.year, target.month)[1]
        return target.replace(day=last_day)

    return target


def get_next_recurrence_date(task):
    """
    Returns the next expected recurrence datetime
    with correct end-of-month handling.
    """

    base_date = task.last_auto_created_at or task.created_at

    if task.recurrence_period == "Monthly":
        return add_months_safe(base_date, 1)

    if task.recurrence_period == "Quarterly":
        return add_months_safe(base_date, 3)

    if task.recurrence_period == "Yearly":
        return add_months_safe(base_date, 12)

    return None


def is_task_due_for_recurrence(task):
    next_due = get_next_recurrence_date(task)
    if not next_due:
        return False

    return date.today() >= next_due.date()


