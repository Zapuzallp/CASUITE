from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView
from django.contrib.auth.models import User

from .models import (Client, )


# RequestedDocument, DocumentMaster, ClientDocumentUpload, DocumentRequest)
# from .forms import ClientForm, CompanyDetailsForm, LLPDetailsForm, OPCDetailsForm, Section8CompanyDetailsForm, \
#     HUFDetailsForm
# from datetime import datetime

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta


# Import your models
from home.models import Client
from home.models import Task, TaskAssignmentStatus

from django.contrib.auth.decorators import login_required


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()

        # =========================================================
        # 1. GLOBAL STATISTICS & FINANCIALS
        # =========================================================
        all_tasks = Task.objects.all()

        # Single query aggregation for performance
        stats = all_tasks.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='Completed')),
            # Active working states
            pending=Count('id', filter=Q(
                status__in=['Pending', 'In Progress', 'Data Collection'])),
            # Approval queue
            review=Count('id', filter=Q(status='Review')),
            # Overdue logic
            overdue=Count('id', filter=Q(due_date__lt=today)
                          & ~Q(status='Completed')),

            # Financials
            billed=Sum('agreed_fee', filter=Q(fee_status='Billed')),
            paid=Sum('agreed_fee', filter=Q(fee_status='Paid')),
            unbilled=Sum('agreed_fee', filter=Q(fee_status='Unbilled'))
        )

        # Client Counts
        total_clients = Client.objects.count()
        new_clients = Client.objects.filter(
            created_at__month=today.month).count()

        # =========================================================
        # 2. REPORT: SERVICE DISTRIBUTION (Donut Chart)
        # =========================================================
        # Count tasks per service type
        service_counts = all_tasks.values('service_type').annotate(
            count=Count('id')).order_by('-count')
        service_chart_data = [{'name': x['service_type'],
                               'value': x['count']} for x in service_counts]

        # =========================================================
        # 3. REPORT: TASK AGING (Pie Chart)
        # =========================================================
        # Get creation dates of open tasks
        open_tasks = all_tasks.exclude(status='Completed').values('created_at')

        aging_data = {'0-7 Days': 0, '8-15 Days': 0,
                      '15-30 Days': 0, '30+ Days': 0}

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
            task__status__in=['Pending', 'In Progress',
                              'Review']  # Only active workflows
        ).select_related('task', 'task__client').order_by('task__due_date')

        my_actions_count = my_actionable_items.count()

        # =========================================================
        # 6. RECENT ACTIVITY TABLE
        # =========================================================
        recent_tasks = all_tasks.select_related('client').prefetch_related(
            'assignees').order_by('-created_at')[:6]

        # =========================================================
        # CONTEXT PACKAGING
        # =========================================================
        context.update({
            'today': today,

            # Summary Stats
            'total_clients': total_clients,
            'new_clients': new_clients,
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
        })

        return context


class ClientView(LoginRequiredMixin, ListView):
    """View for displaying client list page"""
    model = Client
    template_name = 'client/clients_all.html'
    context_object_name = 'clients'
    paginate_by = 10


@login_required
def clock_toggle(request):
    if request.method == 'POST':
        user = request.user
        # Find the most recent active visit
        active_visit = user.visits.filter(check_out__isnull=True).first()

        if active_visit:
            # Clock Out
            active_visit.check_out = timezone.now()
            active_visit.save()
        else:
            # Clock In
            WorkVisit.objects.create(worker=user, check_in=timezone.now())

    # Redirect to whichever page the user was just on, or a main dashboard
    # Change 'dashboard_name' to the name of your main view URL
    return redirect('dashboard_name')
