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


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()

        # =========================================================
        # 1. HIGH-LEVEL SUMMARY (CARDS)
        # =========================================================
        all_tasks = Task.objects.all()

        # Aggregate Global Stats
        stats = all_tasks.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='Completed')),
            pending=Count('id', filter=Q(status__in=['Pending', 'In Progress', 'Data Collection'])),
            review=Count('id', filter=Q(status='Review')),
            overdue=Count('id', filter=Q(due_date__lt=today) & ~Q(status='Completed')),
            # Financials
            billed=Sum('agreed_fee', filter=Q(fee_status='Billed')),
            paid=Sum('agreed_fee', filter=Q(fee_status='Paid')),
            unbilled=Sum('agreed_fee', filter=Q(fee_status='Unbilled'))
        )

        # Client Counts
        total_clients = Client.objects.count()
        new_clients = Client.objects.filter(created_at__month=today.month).count()

        # =========================================================
        # 2. REPORT: TASK AGING ANALYSIS
        # =========================================================
        # Group open tasks by how long they have been open
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
        # 3. REPORT: TOP SOLVERS (LEADERBOARD)
        # =========================================================
        # Count completed assignment parts per user
        top_solvers = User.objects.filter(is_active=True).annotate(
            solved_count=Count('taskassignmentstatus',
                               filter=Q(taskassignmentstatus__is_completed=True))
        ).order_by('-solved_count')[:5]

        # =========================================================
        # 4. USER SPECIFIC & LISTS
        # =========================================================
        # My Actions
        my_actions = TaskAssignmentStatus.objects.filter(
            user=user, is_completed=False
        ).count()

        # Recent Activity
        recent_tasks = all_tasks.select_related('client').prefetch_related('assignees').order_by('-created_at')[:6]

        # Upcoming Deadlines
        next_week = today + timedelta(days=7)
        deadlines = all_tasks.filter(
            status__in=['Pending', 'In Progress'],
            due_date__range=[today, next_week]
        ).order_by('due_date')[:5]

        # =========================================================
        # CONTEXT PACKAGING
        # =========================================================
        context.update({
            'today': today,

            # Summary Cards
            'total_clients': total_clients,
            'new_clients': new_clients,
            'total_tasks': stats['total'],
            'completed_tasks': stats['completed'],
            'pending_tasks': stats['pending'],
            'review_tasks': stats['review'],
            'overdue_tasks': stats['overdue'],

            # Financials (Handle None)
            'total_billed': stats['billed'] or 0,
            'total_paid': stats['paid'] or 0,
            'total_unbilled': stats['unbilled'] or 0,

            # Reports
            'aging_data': aging_data,
            'top_solvers': top_solvers,

            # Lists & User
            'my_actions': my_actions,
            'recent_tasks': recent_tasks,
            'deadlines': deadlines,
        })

        return context


class ClientView(LoginRequiredMixin, ListView):
    """View for displaying client list page"""
    model = Client
    template_name = 'client/clients_all.html'
    context_object_name = 'clients'
    paginate_by = 10