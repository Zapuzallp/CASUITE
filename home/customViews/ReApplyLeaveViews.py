# views.py - for reapplying rejected views
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views import View
from datetime import date
from home.models import Leave , Employee


@login_required
def leave_reapply(request, pk):
    """
    Simple re-apply view for rejected leaves
    """
    if request.method != 'POST':
        messages.warning(request, 'Invalid request method.')
        return redirect('leave-apply')

    try:
        # Get the employee for current user
        employee = request.user.employee

        # Get the rejected leave
        old_leave = Leave.objects.get(
            pk=pk,
            employee=employee,
            status='rejected'
        )
        # check if dates are in the past
        if old_leave.start_date < date.today():
            messages.error(request,f'Cannot re-apply past leaves . The leave dates ({old_leave.start_date}) to {old_leave.end_date} are in the past .')
            return redirect('leave-apply')
        # check end date
        if old_leave.end_date < date.today():
            messages.error(request,
                           f'Cannot re-apply expired leaves. The leave end on  {old_leave.end_date} ')
            return redirect('leave-apply')


        # Create new leave with same details
        Leave.objects.create(
            employee=employee,
            leave_type=old_leave.leave_type,
            start_date=old_leave.start_date,
            end_date=old_leave.end_date,
            reason=old_leave.reason,
            status='pending'
        )

        messages.success(request, 'Leave application re-submitted successfully!')


    except Employee.DoesNotExist:
        messages.error(request, 'Employee profile not found.')
    except Leave.DoesNotExist:
        messages.error(request, 'Leave not found or cannot be re-applied.')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')


    return redirect('leave-apply')