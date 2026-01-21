from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from datetime import date, time, datetime
from math import radians, cos, sin, asin, sqrt

from home.models import Attendance, Leave, Employee, OfficeDetails
from home.customViews.attendanceView import ClockInView, ClockOutView


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters using Haversine formula"""
    if not all([lat1, lon1, lat2, lon2]):
        return None
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Earth radius in meters
    return c * r


def get_location_name(latitude, longitude):
    """Get location name from coordinates (placeholder - integrate with geocoding service)"""
    if not latitude or not longitude:
        return None
    # Convert to float for formatting
    try:
        lat = float(latitude)
        lng = float(longitude)
        return f"Location ({lat:.4f}, {lng:.4f})"
    except (ValueError, TypeError):
        return f"Location ({latitude}, {longitude})"


def check_attendance_compliance(user, clock_in_time, clock_out_time=None, clock_in_lat=None, clock_in_lng=None, clock_out_lat=None, clock_out_lng=None):
    """Check if attendance meets compliance rules"""
    issues = []
    
    try:
        employee = Employee.objects.get(user=user)
        office = employee.office_location
        
        # Standard work hours: 9:30 AM - 6:30 PM with 20-minute tolerance
        standard_start = time(9, 10)  # 9:30 - 20 mins = 9:10
        standard_start_late = time(9, 50)  # 9:30 + 20 mins = 9:50
        standard_end_early = time(18, 10)  # 6:30 - 20 mins = 6:10
        standard_end = time(18, 50)  # 6:30 + 20 mins = 6:50
        
        # Check clock-in compliance
        if clock_in_time:
            clock_in_time_only = clock_in_time.time()
            
            # Late arrival beyond tolerance
            if clock_in_time_only > standard_start_late:
                late_minutes = (datetime.combine(date.today(), clock_in_time_only) - 
                              datetime.combine(date.today(), time(9, 30))).seconds // 60
                issues.append(f"Late arrival by {late_minutes} minutes")
            
            # Check location for clock-in
            if clock_in_lat and clock_in_lng and office and office.latitude and office.longitude:
                distance = calculate_distance(clock_in_lat, clock_in_lng, office.latitude, office.longitude)
                if distance and distance > 100:
                    issues.append(f"Clocked in {distance:.0f}m away from office")
        
        # Check clock-out compliance
        if clock_out_time:
            clock_out_time_only = clock_out_time.time()
            
            # Early departure beyond tolerance
            if clock_out_time_only < standard_end_early:
                early_minutes = (datetime.combine(date.today(), time(18, 30)) - 
                               datetime.combine(date.today(), clock_out_time_only)).seconds // 60
                issues.append(f"Early departure by {early_minutes} minutes")
            
            # Check location for clock-out
            if clock_out_lat and clock_out_lng and office and office.latitude and office.longitude:
                distance = calculate_distance(clock_out_lat, clock_out_lng, office.latitude, office.longitude)
                if distance and distance > 100:
                    issues.append(f"Clocked out {distance:.0f}m away from office")
    
    except Employee.DoesNotExist:
        issues.append("Employee profile not found")
    
    return issues


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
    """Mobile clock in with location and compliance checking"""
    today = date.today()
    current_time = timezone.now()
    
    # Get location data
    latitude = request.POST.get('latitude')
    longitude = request.POST.get('longitude')
    location_name = request.POST.get('location_name')  # Get from form like web app
    
    # Use provided location name or generate from coordinates
    if not location_name and latitude and longitude:
        location_name = get_location_name(latitude, longitude)
    
    # Get or create attendance record
    attendance, created = Attendance.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={
            'clock_in': current_time,
            'clock_in_lat': latitude,
            'clock_in_long': longitude,
            'location_name': location_name,
            'status': 'pending'  # Default to pending, will be updated based on compliance
        }
    )
    
    if not created and not attendance.clock_in:
        attendance.clock_in = current_time
        attendance.clock_in_lat = latitude
        attendance.clock_in_long = longitude
        attendance.location_name = location_name
    
    # Check compliance for clock-in only
    compliance_issues = check_attendance_compliance(
        request.user, current_time, 
        clock_in_lat=latitude, clock_in_lng=longitude
    )
    
    # Set status and remarks based on compliance
    if compliance_issues:
        attendance.status = 'pending'
        attendance.remark = "; ".join(compliance_issues)
        messages.warning(request, f"Attendance marked as pending: {'; '.join(compliance_issues)}")
    else:
        attendance.status = 'approved'
        messages.success(request, 'Clocked in successfully!')
    
    attendance.save()
    return redirect('mobile_attendance')


@login_required
@require_http_methods(["POST"])
def mobile_clock_out(request):
    """Mobile clock out with location and compliance checking"""
    today = date.today()
    current_time = timezone.now()
    
    # Get location data
    latitude = request.POST.get('latitude')
    longitude = request.POST.get('longitude')
    
    try:
        attendance = Attendance.objects.get(user=request.user, date=today)
        
        if attendance.clock_in and not attendance.clock_out:
            attendance.clock_out = current_time
            attendance.clock_out_lat = latitude
            attendance.clock_out_long = longitude
            
            # Update location name if not set
            if not attendance.location_name and latitude and longitude:
                attendance.location_name = get_location_name(latitude, longitude)
            
            # Check full compliance (both clock-in and clock-out)
            compliance_issues = check_attendance_compliance(
                request.user, attendance.clock_in, current_time,
                attendance.clock_in_lat, attendance.clock_in_long,
                latitude, longitude
            )
            
            # Set final status based on compliance
            if compliance_issues:
                attendance.status = 'pending'
                attendance.remark = "; ".join(compliance_issues)
                messages.warning(request, f"Attendance marked as pending: {'; '.join(compliance_issues)}")
            else:
                attendance.status = 'approved'
                attendance.remark = "On-time attendance within office premises"
                messages.success(request, 'Clocked out successfully!')
            
            attendance.save()
        else:
            messages.error(request, 'No active clock-in found or already clocked out.')
            
    except Attendance.DoesNotExist:
        messages.error(request, 'No attendance record found for today.')
    
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