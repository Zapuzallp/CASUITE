from home.models import Task,TaskAssignmentStatus
from django.db.models import Count, Sum, Q, OuterRef, Subquery
from django.utils import timezone
from home.clients.client_access import get_accessible_clients


def get_client_dashboard_data(user, today):
    
    """
    Handles:
    1. Client entitlement
    2. Client counts
    3. Client distribution chart data
    """

    # ---------------------------------------------------------
    # 1. CLIENT VISIBILITY (ENTITLEMENT)
    # # ---------------------------------------------------------
    clients_qs = get_accessible_clients(user)
    # ---------------------------------------------------------
    # 2. CLIENT COUNTS
    # ---------------------------------------------------------
    total_clients = clients_qs.count()
    new_clients = clients_qs.filter(
        created_at__month=today.month,
        created_at__year=today.year
    ).count()

    # ---------------------------------------------------------
    # 3. CLIENT DISTRIBUTION (PIE CHART)
    # ---------------------------------------------------------
    distribution_qs = (
        clients_qs
        .values('client_type', 'business_structure')
        .annotate(count=Count('id'))
    )

    client_distribution_chart_data = []

    for row in distribution_qs:
        if row['client_type'] == 'Individual':
            label = 'Individual'
        else:
            label = row['business_structure'] or 'Entity'

        client_distribution_chart_data.append({
            'name': label,
            'value': row['count']
        })

    # ---------------------------------------------------------
    # 4. RETURN PACKAGED DATA
    # ---------------------------------------------------------
    return {
        'total_clients': total_clients,
        'new_clients': new_clients,
        'client_distribution_chart_data': client_distribution_chart_data,
    }


def get_performance_cards(user):
    
    today = timezone.now().date()

    all_tasks = Task.objects.all()
    
    if not user.is_superuser:
        all_tasks = all_tasks.filter(client__assigned_ca=user)
    
     # Add attendance data for dashboard display
    from home.models import Attendance
    attendance = Attendance.objects.filter(
            user=user,
            date=today
    ).first()
    # =========================================================
    # 1. GLOBAL STATISTICS & FINANCIALS
    # =========================================================

    stats = all_tasks.aggregate(
           
        # Active working states
        pending=Count('id', filter=~Q(status__in=['GSTR Submit', 'Delivered', 'Completed'])),

        # Financials
        billed=Sum('agreed_fee', filter=Q(fee_status='Billed')),
        paid=Sum('agreed_fee', filter=Q(fee_status='Paid')),

        )

    # =========================================================
    # 2. USER SPECIFIC ACTIONS (Clickable)
    # =========================================================
    # "My Action Items" - Specific steps waiting for the logged-in user
    
    first_incomplete_order = TaskAssignmentStatus.objects.filter(
            task=OuterRef('task_id'),
            is_completed=False
        ).order_by('order').values('order')[:1]    
    

    # Now filter steps for the current user that match that specific 'first' order
    my_actionable_items = TaskAssignmentStatus.objects.filter(
            user=user,
            is_completed=False,
            order=Subquery(first_incomplete_order)
        ).select_related('task', 'task__client').order_by('task__due_date')

    my_actions_count = my_actionable_items.count()

    # 3. CLIENT Distribution REPORT (PIE CHART)
    # =========================================================
    
    client_data = get_client_dashboard_data(user, today)
    
    context = {

            # Summary Stats
            'total_clients': client_data['total_clients'],
            'new_clients': client_data['new_clients'],
            'pending_tasks': stats['pending'],
            'my_actionable_items': my_actionable_items[:6],  # Show top 6
            
            # Financials (Handle None if DB empty)
            'total_billed': stats['billed'] or 0,
            'total_paid': stats['paid'] or 0,
            'client_distribution_chart_data': client_data['client_distribution_chart_data'],

            # Lists
            'my_actions_count': my_actions_count,
            'attendence':attendance,
          
        }
        
    return context  
