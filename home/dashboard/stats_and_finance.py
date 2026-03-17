from home.models import Task
from django.db.models import Count,Q,Sum
from django.utils import timezone

def stats_and_finance(user):
    today = timezone.now().date()

    all_tasks = Task.objects.all()
    if not user.is_superuser:
        all_tasks = all_tasks.filter(client__assigned_ca=user)

    # Single query aggregation for performance
    stats = all_tasks.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='Completed')),
        # Approval queue
        review=Count('id', filter=Q(status='Review')),
        # Overdue logic
        overdue=Count('id', filter=Q(due_date__lt=today) & ~Q(status='Completed')),
        # Financials
        unbilled=Sum('agreed_fee', filter=Q(fee_status='Unbilled'))
    )

    
    # =========================================================
    # 1. REPORT: SERVICE DISTRIBUTION (Donut Chart)
    # =========================================================
    # Count tasks per service type
    service_counts = all_tasks.values('service_type').annotate(count=Count('id')).order_by('-count')
    service_chart_data = [{'name': x['service_type'], 'value': x['count']} for x in service_counts]
    
    # =========================================================
    # 2. REPORT: TASK AGING (Pie Chart)
    # =========================================================
    # Get creation dates of open tasks
    open_tasks = all_tasks.exclude(status='Completed').values('created_at')

    aging_data = {'0-7 Days': 0, '8-15 Days': 0, '15-30 Days': 0, '30+ Days': 0}

    for t in open_tasks:
        age = (timezone.now() - t['created_at']).days
        if age <= 7:
            aging_data['0-7 Days'] += 1
        elif age <= 15:
            aging_data['8-15 Days'] += 1
        elif age <= 30:
            aging_data['15-30 Days'] += 1
        else:
            aging_data['30+ Days'] += 1
    
    context = {
            # Summary Stats
            'total_tasks': stats['total'],
            'completed_tasks': stats['completed'],
          
            'review_tasks': stats['review'],
            'overdue_tasks': stats['overdue'],

            # Financials (Handle None if DB empty)
            'total_unbilled': stats['unbilled'] or 0,

            # Chart Data
            'service_chart_data': service_chart_data,
            'aging_data': aging_data,
    }
    return context