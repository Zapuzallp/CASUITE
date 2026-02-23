
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from ..models import Leave, Employee
from django.views.generic import TemplateView
from home.mixin import *
from django.contrib.auth.mixins import LoginRequiredMixin

def is_admin(user):
    return user.is_staff or user.is_superuser


class ManageLeavesView(LoginRequiredMixin, AdminAccessMixin, TemplateView):
    template_name = "manage_leaves.html"

    def post(self, request, *args, **kwargs):
        leave_id = request.POST.get('leave_id')
        status = request.POST.get('status')

        if leave_id and status in ['approved', 'rejected']:
            leave = get_object_or_404(Leave, id=leave_id)
            leave.status = status
            leave.save()
            messages.success(request, f'Leave {status} successfully!')
            return redirect('manage-leaves')

        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        employees = Employee.objects.all()

        # Role-based leave filtering
        if request.user.employee.role == 'BRANCH_MANAGER':
            all_leaves = (
                Leave.objects.all()
                .exclude(employee=request.user.employee)
                .select_related('employee__user')
                .order_by('-created_at')
                .filter(employee__office_location=request.user.employee.office_location)
            )

        elif request.user.is_superuser or request.user.employee.role == 'ADMIN':
            all_leaves = (
                Leave.objects.all()
                .select_related('employee__user')
                .order_by('-created_at')
            )
        else:
            all_leaves = Leave.objects.none()

        leaves_with_data = []

        for leave in all_leaves:
            total_earlier_leaves = Leave.objects.filter(
                employee=leave.employee,
                status='approved',
                created_at__lt=leave.created_at
            ).count()

            leaves_with_data.append({
                'id': leave.id,
                'user': leave.employee.user,
                'employee': leave.employee,
                'leave_type': leave.leave_type,
                'get_leave_type_display': leave.get_leave_type_display(),
                'start_date': leave.start_date,
                'end_date': leave.end_date,
                'total_days': leave.duration,
                'reason': leave.reason,
                'status': leave.status,
                'created_at': leave.created_at,
                'total_earlier_leaves': total_earlier_leaves,
            })

        # Counts
        context['all_leaves'] = leaves_with_data
        context['total_pending'] = len([l for l in leaves_with_data if l['status'] == 'pending'])
        context['total_approved'] = len([l for l in leaves_with_data if l['status'] == 'approved'])
        context['total_rejected'] = len([l for l in leaves_with_data if l['status'] == 'rejected'])
        context['employees'] = employees

        return context


