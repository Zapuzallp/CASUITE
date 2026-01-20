from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from datetime import date

from home.models import Attendance, Leave, Employee
from home.customViews.attendanceView import ClockInView, ClockOutView


def mobile_login_view(request):
    """Mobile login page"""
    if request.user.is_authenticated:
        return redirect('mobile_attendance')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('mobile_attendance')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'mobile_login.html')


@login_required
def mobile_logout_view(request):
    """Mobile logout"""
    logout(request)
    return redirect('mobile_login')


@login_required
@require_http_methods(["POST"])
def mobile_clock_in(request):
    """Mobile clock in using existing web logic"""
    view = ClockInView.as_view()
    response = view(request)
    return redirect('mobile_attendance')


@login_required
@require_http_methods(["POST"])
def mobile_clock_out(request):
    """Mobile clock out using existing web logic"""
    view = ClockOutView.as_view()
    response = view(request)
    return redirect('mobile_attendance')


@login_required
def mobile_attendance_view(request):
    """Mobile attendance page view"""
    today = date.today()
    
    # Get current attendance record
    current_attendance = Attendance.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    # Get employee profile and leave summary
    try:
        employee = Employee.objects.get(user=request.user)
        leave_summary = employee.get_leave_summary()
    except Employee.DoesNotExist:
        # Create a default leave summary if employee profile doesn't exist
        leave_summary = {
            'casual': {'remaining': 8, 'taken': 0, 'allotted': 8},
            'sick': {'remaining': 7, 'taken': 0, 'allotted': 7},
            'earned': {'remaining': 5, 'taken': 0, 'allotted': 5}
        }
    
    # Get recent leaves (last 5)
    try:
        recent_leaves = Leave.objects.filter(
            employee__user=request.user
        ).order_by('-created_at')[:5]
    except:
        recent_leaves = []
    
    context = {
        'current_attendance': current_attendance,
        'leave_summary': leave_summary,
        'recent_leaves': recent_leaves,
        'current_date': today.strftime('%b %d, %Y'),
        'user': request.user,
    }
    
    return render(request, 'mobile_attendance.html', context)


@login_required
def mobile_logs_view(request):
    """Mobile logs using existing web logic"""
    from home.customViews.attendanceView import AttendanceLogsView
    view = AttendanceLogsView.as_view()
    response = view(request)
    if hasattr(response, 'context_data'):
        logs = response.context_data.get('logs', [])
    else:
        logs = Attendance.objects.filter(user=request.user).order_by('-date')
    return render(request, 'mobile_logs.html', {'logs': logs})


@login_required
@require_http_methods(["POST"])
def mobile_apply_leave(request):
    """Mobile leave application using existing web logic"""
    from home.customViews.leaveView import LeaveCreateView
    view = LeaveCreateView.as_view()
    response = view(request)
    return redirect('mobile_attendance')