from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView
from django.contrib.auth.models import User

from .models import (Client,ClientUserEntitle )


# RequestedDocument, DocumentMaster, ClientDocumentUpload, DocumentRequest)
# from .forms import ClientForm, CompanyDetailsForm, LLPDetailsForm, OPCDetailsForm, Section8CompanyDetailsForm, \
#     HUFDetailsForm
# from datetime import datetime

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from django.utils import timezone
from home.clients.client_access import get_accessible_clients
from datetime import timedelta

# Import your models
from home.models import Client
from home.models import Task, TaskAssignmentStatus


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()

        # Add attendance data for dashboard display
        from home.models import Attendance
        attendance = Attendance.objects.filter(
            user=user,
            date=today
        ).first()

        # =========================================================
        # 1. GLOBAL STATISTICS & FINANCIALS
        # =========================================================
        all_tasks = Task.objects.all()
        if not user.is_superuser:
            all_tasks = all_tasks.filter(client__assigned_ca=user)

        # Single query aggregation for performance
        stats = all_tasks.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='Completed')),
            # Active working states
            pending=Count('id', filter=Q(status__in=['Pending', 'In Progress', 'Data Collection'])),
            # Approval queue
            review=Count('id', filter=Q(status='Review')),
            # Overdue logic
            overdue=Count('id', filter=Q(due_date__lt=today) & ~Q(status='Completed')),

            # Financials
            billed=Sum('agreed_fee', filter=Q(fee_status='Billed')),
            paid=Sum('agreed_fee', filter=Q(fee_status='Paid')),
            unbilled=Sum('agreed_fee', filter=Q(fee_status='Unbilled'))
        )

        # =========================================================
        # 2. REPORT: SERVICE DISTRIBUTION (Donut Chart)
        # =========================================================
        # Count tasks per service type
        service_counts = all_tasks.values('service_type').annotate(count=Count('id')).order_by('-count')
        service_chart_data = [{'name': x['service_type'], 'value': x['count']} for x in service_counts]

        # =========================================================
        # 3. REPORT: TASK AGING (Pie Chart)
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

        # =========================================================
        # 4. REPORT: LEADERBOARD (Top Solvers)
        # =========================================================
        # Count completed assignment steps per user (Collaborative Score)
        top_solvers = User.objects.filter(is_active=True).annotate(
            solved_count=Count('taskassignmentstatus',
                               filter=Q(taskassignmentstatus__is_completed=True))
        ).order_by('-solved_count')[:5]

        # =========================================================
        # 5. USER SPECIFIC ACTIONS (Clickable)
        # =========================================================
        # "My Action Items" - Specific steps waiting for the logged-in user
        my_actionable_items = TaskAssignmentStatus.objects.filter(
            user=user,
            is_completed=False,
            task__status__in=['Pending', 'In Progress', 'Review']  # Only active workflows
        ).select_related('task', 'task__client').order_by('task__due_date')

        my_actions_count = my_actionable_items.count()

        # =========================================================
        # 6. RECENT ACTIVITY TABLE
        # =========================================================
        recent_tasks = all_tasks.select_related('client').prefetch_related('assignees').order_by('-created_at')[:6]

        # =========================================================
        # 7. CLIENT Distribution REPORT (PIE CHART)
        # =========================================================
        client_data = get_client_dashboard_data(user, today)

        # =========================================================
        # 8. DUE TASKS FOR DASHBOARD MODULE
        # =========================================================
        due_range = self.request.GET.get('due_range', 'overdue')  # Default to overdue

        # Base queryset with role-based visibility (same as all_tasks)
        due_tasks_qs = all_tasks.exclude(status='Completed')

        # Apply date range filter
        if due_range == 'overdue':
            due_tasks_qs = due_tasks_qs.filter(due_date__lt=today)
        elif due_range == 'today':
            due_tasks_qs = due_tasks_qs.filter(due_date=today)
        elif due_range == 'tomorrow':
            due_tasks_qs = due_tasks_qs.filter(due_date=today + timedelta(days=1))
        elif due_range == '5days':
            due_tasks_qs = due_tasks_qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=5))
        elif due_range == '10days':
            due_tasks_qs = due_tasks_qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=10))
        elif due_range == '15days':
            due_tasks_qs = due_tasks_qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=15))
        elif due_range == '30days':
            due_tasks_qs = due_tasks_qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=30))

        due_tasks = due_tasks_qs.select_related('client').prefetch_related('assignees').order_by('due_date')[:20]

        # =========================================================
        # CONTEXT PACKAGING
        # =========================================================
        context.update({
            'today': today,

            # Summary Stats
            'total_clients': client_data['total_clients'],
            'new_clients': client_data['new_clients'],
            'total_tasks': stats['total'],
            'completed_tasks': stats['completed'],
            'pending_tasks': stats['pending'],
            'review_tasks': stats['review'],
            'overdue_tasks': stats['overdue'],

            # Financials (Handle None if DB empty)
            'total_billed': stats['billed'] or 0,
            'total_paid': stats['paid'] or 0,
            'total_unbilled': stats['unbilled'] or 0,

            # Chart Data
            'service_chart_data': service_chart_data,
            'aging_data': aging_data,

            # Lists
            'top_solvers': top_solvers,
            'my_actionable_items': my_actionable_items[:6],  # Show top 6
            'my_actions_count': my_actions_count,
            'recent_tasks': recent_tasks,

            # Due Tasks Module
            'due_tasks': due_tasks,
            'due_range': due_range,

            #clients
            'client_distribution_chart_data': client_data['client_distribution_chart_data'],
        })

        return context

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

@login_required(login_url='/login/')
def client_search(request):
    q = request.GET.get('q', '').strip()

    clients = Client.objects.filter(
        Q(client_name__icontains=q) |
        Q(pan_no__icontains=q)
    )[:20]

    data = []
    for c in clients:
        data.append({
            "id": c.id,
            "text": f"{c.client_name} || {c.pan_no} || {c.status}"
        })
    return JsonResponse(data, safe=False)

# =========================================================
# AJAX VIEW FOR DUE TASKS FILTERING
# =========================================================
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string

@login_required
def due_tasks_ajax(request):
    """Return Due Tasks as JSON for AJAX filtering"""
    from django.http import JsonResponse
    
    user = request.user
    today = timezone.now().date()
    
    # Get all tasks (with role-based visibility)
    all_tasks = Task.objects.all()
    if not user.is_superuser:
        all_tasks = all_tasks.filter(client__assigned_ca=user)
    
    due_range = request.GET.get('due_range', 'overdue')
    
    # Base queryset
    due_tasks_qs = all_tasks.exclude(status='Completed')
    
    # Apply date range filter
    if due_range == 'overdue':
        due_tasks_qs = due_tasks_qs.filter(due_date__lt=today)
    elif due_range == 'today':
        due_tasks_qs = due_tasks_qs.filter(due_date=today)
    elif due_range == 'tomorrow':
        due_tasks_qs = due_tasks_qs.filter(due_date=today + timedelta(days=1))
    elif due_range == '5days':
        due_tasks_qs = due_tasks_qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=5))
    elif due_range == '10days':
        due_tasks_qs = due_tasks_qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=10))
    elif due_range == '15days':
        due_tasks_qs = due_tasks_qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=15))
    elif due_range == '30days':
        due_tasks_qs = due_tasks_qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=30))
    
    due_tasks = due_tasks_qs.select_related('client').prefetch_related('assignees').order_by('due_date')[:20]
    
    # Build JSON response
    tasks_data = []
    for task in due_tasks:
        assignees = [a.get_full_name() or a.username for a in task.assignees.all()[:2]]
        tasks_data.append({
            'id': task.id,
            'title': task.task_title[:30] + '...' if len(task.task_title) > 30 else task.task_title,
            'client': task.client.client_name if task.client else '-',
            'service': task.get_service_type_display() or '-',
            'due_date': task.due_date.strftime('%b %d, %Y') if task.due_date else '-',
            'due_date_class': 'text-danger' if task.due_date and task.due_date < today else ('text-warning' if task.due_date == today else 'text-success'),
            'assignees': assignees,
            'status': task.get_status_display(),
            'status_class': task.status.lower() if task.status else 'secondary',
        })
    
    # Map due_range to display text
    range_labels = {
        'overdue': 'Overdue Tasks',
        'today': 'Due Today',
        'tomorrow': 'Due Tomorrow',
        '5days': 'Due in 5 Days',
        '10days': 'Due in 10 Days',
        '15days': 'Due in 15 Days',
        '30days': 'Due in 30 Days',
    }
    
    return JsonResponse({
        'tasks': tasks_data,
        'count': len(tasks_data),
        'due_range': due_range,
        'range_label': range_labels.get(due_range, 'All Due Tasks'),
    })

