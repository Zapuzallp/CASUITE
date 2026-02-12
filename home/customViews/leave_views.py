
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from ..models import Leave, Employee


def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def manage_leaves(request):
    employees = Employee.objects.all()

    if request.method == 'POST':
        leave_id = request.POST.get('leave_id')
        status = request.POST.get('status')
        if leave_id and status in ['approved', 'rejected']:
            leave = get_object_or_404(Leave, id=leave_id)
            leave.status = status
            leave.save()
            messages.success(request, f'Leave {status} successfully!')
            return redirect('manage-leaves')
           
    # Get ALL leaves with employee data
    if request.user.employee.role == 'BRANCH_MANAGER':
        all_leaves = (
        Leave.objects.all()
        .exclude(employee=request.user.employee)
        .select_related('employee__user')
        .order_by('-created_at')
        )
        all_leaves = all_leaves.filter(employee__office_location = request.user.employee.office_location)

    elif request.user.is_superuser or request.user.employee.role == 'ADMIN':
        all_leaves = (Leave.objects.all().select_related('employee__user').order_by('-created_at'))
    else:
        all_leaves = Leave.objects.none()
   
    # Prepare data for template
    leaves_with_data = []

    for leave in all_leaves:
        # Calculate total earlier APPROVED leaves for this employee
        total_earlier_leaves = Leave.objects.filter(
            employee=leave.employee,
            status='approved',
            created_at__lt=leave.created_at
        ).count()

        leaves_with_data.append({
            'id': leave.id,
            'user': leave.employee.user,  # Access user through employee
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

    # Get counts
    pending_leaves = [l for l in leaves_with_data if l['status'] == 'pending']
    total_pending = len(pending_leaves)
    total_approved = len([l for l in leaves_with_data if l['status'] == 'approved'])
    total_rejected = len([l for l in leaves_with_data if l['status'] == 'rejected'])

    context = {
        'all_leaves': leaves_with_data,
        'total_pending': total_pending,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'employees':employees,
    }
    return render(request, 'manage_leaves.html', context)


