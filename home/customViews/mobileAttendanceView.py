from typing import Optional

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from datetime import date

from home.models import Attendance, Leave, Employee
from home.utils import process_clock_in, process_clock_out


def mobile_login_view(request):
    """Mobile login using Django's built-in authentication"""
    if request.user.is_authenticated:
        return redirect('mobile_attendance')
    
    # Clear any existing messages when accessing login page
    from django.contrib import messages
    storage = messages.get_messages(request)
    storage.used = True
    
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
    return redirect('logout')


@login_required
@require_http_methods(["POST"])
def mobile_clock_in(request):
    """Mobile clock in using utility functions"""
    lat = request.POST.get("lat")
    long = request.POST.get("long")
    location_name = request.POST.get("location_name")
    
    result = process_clock_in(request.user, lat, long, location_name)
    
    if result['success']:
        messages.success(request, result['message'])
    else:
        messages.warning(request, result['message'])
    
    return redirect('mobile_attendance')


@login_required
@require_http_methods(["POST"])
def mobile_clock_out(request):
    """Mobile clock out using utility functions"""
    lat = request.POST.get("lat")
    long = request.POST.get("long")
    location_name = request.POST.get("location_name")
    
    result = process_clock_out(request.user, lat, long, location_name)
    
    if result['success']:
        messages.success(request, result['message'])
    else:
        messages.error(request, result['message'])
    
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
    
    # Determine button states
    can_clock_in = True
    can_clock_out = False
    
    if current_attendance:
        if current_attendance.clock_in and current_attendance.clock_out:
            # Already completed for the day
            can_clock_in = False
            can_clock_out = False
        elif current_attendance.clock_in and not current_attendance.clock_out:
            # Clocked in, can clock out
            can_clock_in = False
            can_clock_out = True
    
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
        'can_clock_in': can_clock_in,
        'can_clock_out': can_clock_out,
        'leave_summary': leave_summary,
        'recent_leaves': recent_leaves,
        'current_date': today.strftime('%b %d, %Y'),
        'user': request.user,
    }
    
    return render(request, 'mobile_attendance.html', context)


@login_required
def mobile_logs_view(request):
    """Mobile logs showing past 60 days attendance in table format"""
    from datetime import timedelta
    
    # Get attendance logs for past 60 days
    sixty_days_ago = date.today() - timedelta(days=60)
    logs = Attendance.objects.filter(
        user=request.user,
        date__gte=sixty_days_ago
    ).order_by('-date')
    
    return render(request, 'mobile_logs.html', {'logs': logs})


@login_required
def mobile_apply_leave(request):
    """Mobile leave application using existing web logic"""
    from home.customViews.leaveView import LeaveCreateView
    view = LeaveCreateView.as_view()
    response = view(request)
    return redirect('mobile_attendance')


@login_required
def mobile_leave_logs_view(request):
    """Mobile leave logs view"""
    try:
        employee = Employee.objects.get(user=request.user)
        leaves = Leave.objects.filter(employee=employee).order_by('-created_at')
    except Employee.DoesNotExist:
        leaves = []
    
    return render(request, 'mobile_leave_logs.html', {'leaves': leaves})