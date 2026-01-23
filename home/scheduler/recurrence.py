from datetime import date
from dateutil.relativedelta import relativedelta
import calendar

def get_valid_day(year, month, preferred_day):
    last_day = calendar.monthrange(year, month)[1]
    return min(preferred_day, last_day)


def calculate_next_run(anchor_date, base_date, recurrence_period):
    """
    anchor_date : date (task.created_at.date())
    base_date   : datetime (current next_run_at)
    """

    if recurrence_period == "Monthly":
        delta = relativedelta(months=1)
    elif recurrence_period == "Quarterly":
        delta = relativedelta(months=3)
    elif recurrence_period == "Yearly":
        delta = relativedelta(years=1)
    else:
        raise ValueError("Invalid recurrence period")

    target = base_date + delta

    intended_day = anchor_date.day
    corrected_day = get_valid_day(
        target.year,
        target.month,
        intended_day
    )

    return target.replace(day=corrected_day)


def get_next_recurrence_date(recurrence):
    """
    ✔ Deterministic next_run_at calculation
    ✔ Uses existing next_run_at as base
    """

    anchor_date = recurrence.task.created_at.date()
    base_date = (
        recurrence.next_run_at
        if recurrence.next_run_at
        else recurrence.task.created_at
    )

    return calculate_next_run(
        anchor_date=anchor_date,
        base_date=base_date,
        recurrence_period=recurrence.recurrence_period,
    )
