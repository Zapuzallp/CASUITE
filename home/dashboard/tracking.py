from home.models import Task,Leave 
from django.utils import timezone
from datetime import timedelta

def tracking(user):
    today = timezone.now().date()

    all_tasks = Task.objects.all()
    if not user.is_superuser:
        all_tasks = all_tasks.filter(client__assigned_ca=user)
    
    # =========================================================
    # 1. RECENT ACTIVITY TABLE
    # =========================================================

    recent_tasks = all_tasks.select_related('client').prefetch_related('assignees').order_by('-created_at')[:6]
    # =========================================================
    # 2. Employees On Leave Today
    # =========================================================
    
    employees_on_leave_today = (
            Leave.objects
            .filter(start_date__lte=today, end_date__gte=today, status="approved")
            .select_related("employee", "employee__user")
        )

    context={
            'recent_tasks': recent_tasks,
            'employees_on_leave_today': employees_on_leave_today,
    }

    return context 