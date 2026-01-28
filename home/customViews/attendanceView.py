from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import date, datetime, time, timedelta
from django.contrib import messages

from home.models import Attendance, OfficeDetails, EmployeeShift, Employee

from math import radians, cos, sin, asin, sqrt

def get_distance(lat1, lon1, lat2, lon2):
    # Haversine formula
    R = 6371000  # meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def check_web_attendance_compliance(user, clock_in_time, clock_out_time=None, clock_in_lat=None, clock_in_lng=None, clock_out_lat=None, clock_out_lng=None):
    """Check attendance compliance for web app"""
    issues = []
    
    try:
        employee = Employee.objects.get(user=user)
        office = employee.office_location
        
        # Get employee's shift timing
        employee_shift = EmployeeShift.objects.filter(user=user, valid_to__isnull=True).first()
        if employee_shift:
            shift_start = employee_shift.shift.shift_start_time
            shift_end = employee_shift.shift.shift_end_time
            # 20-minute tolerance
            tolerance_minutes = 20
            shift_start_late = (datetime.combine(date.today(), shift_start) + timedelta(minutes=tolerance_minutes)).time()
            shift_end_early = (datetime.combine(date.today(), shift_end) - timedelta(minutes=tolerance_minutes)).time()
        else:
            # Default timing if no shift assigned
            shift_start = time(9, 30)
            shift_end = time(18, 30)
            shift_start_late = time(9, 50)
            shift_end_early = time(18, 10)
        
        # If no office assigned, only check for late login/logout, auto-approve otherwise
        if not office:
            # Check clock-in compliance (only late arrival)
            if clock_in_time:
                clock_in_time_only = clock_in_time.time()
                if clock_in_time_only > shift_start_late:
                    late_minutes = (datetime.combine(date.today(), clock_in_time_only) - 
                                  datetime.combine(date.today(), shift_start)).seconds // 60
                    issues.append(f"Late arrival by {late_minutes} minutes")
            
            # Check clock-out compliance (only early departure)
            if clock_out_time:
                clock_out_time_only = clock_out_time.time()
                if clock_out_time_only < shift_end_early:
                    early_minutes = (datetime.combine(date.today(), shift_end) - 
                                   datetime.combine(date.today(), clock_out_time_only)).seconds // 60
                    issues.append(f"Early departure by {early_minutes} minutes")
            
            return issues
        
        # Office assigned - full compliance check
        # Check clock-in compliance
        if clock_in_time:
            clock_in_time_only = clock_in_time.time()
            
            # Late arrival beyond tolerance
            if clock_in_time_only > shift_start_late:
                late_minutes = (datetime.combine(date.today(), clock_in_time_only) - 
                              datetime.combine(date.today(), shift_start)).seconds // 60
                issues.append(f"Late arrival by {late_minutes} minutes")
            
            # Check location for clock-in
            if clock_in_lat and clock_in_lng and office.latitude and office.longitude:
                distance = get_distance(float(clock_in_lat), float(clock_in_lng), float(office.latitude), float(office.longitude))
                if distance > 100:
                    issues.append(f"Clocked in {distance:.0f}m away from office")
        
        # Check clock-out compliance
        if clock_out_time:
            clock_out_time_only = clock_out_time.time()
            
            # Early departure beyond tolerance
            if clock_out_time_only < shift_end_early:
                early_minutes = (datetime.combine(date.today(), shift_end) - 
                               datetime.combine(date.today(), clock_out_time_only)).seconds // 60
                issues.append(f"Early departure by {early_minutes} minutes")
            
            # Check location for clock-out
            if clock_out_lat and clock_out_lng and office.latitude and office.longitude:
                distance = get_distance(float(clock_out_lat), float(clock_out_lng), float(office.latitude), float(office.longitude))
                if distance > 100:
                    issues.append(f"Clocked out {distance:.0f}m away from office")
    
    except Employee.DoesNotExist:
        issues.append("Employee profile not found")
    
    return issues

class ClockInView(LoginRequiredMixin, View):
    def post(self, request):
        today = date.today()
        current_time = timezone.now()

        attendance, _ = Attendance.objects.get_or_create(
            user=request.user,
            date=today
        )

        if attendance.clock_in:
            messages.warning(request, 'Already clocked in today!')
            return redirect("dashboard")

        lat = request.POST.get("lat")
        long = request.POST.get("long")
        location_name = request.POST.get("location_name")

        attendance.clock_in = current_time
        
        # Only set location fields if they have valid values
        if lat and lat.strip():
            try:
                attendance.clock_in_lat = float(lat)
            except (ValueError, TypeError):
                attendance.clock_in_lat = None
        else:
            attendance.clock_in_lat = None
            
        if long and long.strip():
            try:
                attendance.clock_in_long = float(long)
            except (ValueError, TypeError):
                attendance.clock_in_long = None
        else:
            attendance.clock_in_long = None
            
        if location_name and location_name.strip():
            attendance.location_name = location_name
        else:
            attendance.location_name = None

        # Check compliance for clock-in only
        compliance_issues = check_web_attendance_compliance(
            request.user, current_time, 
            clock_in_lat=lat, clock_in_lng=long
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
        return redirect("dashboard")

class ClockOutView(LoginRequiredMixin, View):
    def post(self, request):
        lat = request.POST.get("lat")
        long = request.POST.get("long")
        current_time = timezone.now()

        attendance = Attendance.objects.filter(
            user=request.user,
            clock_out__isnull=True
        ).last()

        if not attendance:
            messages.error(request, 'No active clock-in found!')
            return redirect("dashboard")

        # Handle forgotten logout
        if current_time.date() > attendance.date:
            attendance.clock_out = timezone.make_aware(
                datetime.combine(attendance.date, time(22, 0))
            )
            attendance.status = "pending"
            attendance.remark = "Auto clock-out (missed logout)"
        else:
            attendance.clock_out = current_time

        # Only set location fields if they have valid values
        if lat and lat.strip():
            try:
                attendance.clock_out_lat = float(lat)
            except (ValueError, TypeError):
                attendance.clock_out_lat = None
        else:
            attendance.clock_out_lat = None
            
        if long and long.strip():
            try:
                attendance.clock_out_long = float(long)
            except (ValueError, TypeError):
                attendance.clock_out_long = None
        else:
            attendance.clock_out_long = None
        
        # Only set location_name if it's completely empty (not set during clock-in)
        # Don't overwrite existing location names with coordinates
        if not attendance.location_name:
            location_name = request.POST.get("location_name")
            if location_name:
                attendance.location_name = location_name
            elif lat and long:
                try:
                    lat_f = float(lat)
                    lng_f = float(long)
                    attendance.location_name = f"Location ({lat_f:.4f}, {lng_f:.4f})"
                except (ValueError, TypeError):
                    attendance.location_name = f"Location ({lat}, {long})"
        
        # Check full compliance (both clock-in and clock-out)
        compliance_issues = check_web_attendance_compliance(
            request.user, attendance.clock_in, attendance.clock_out,
            attendance.clock_in_lat, attendance.clock_in_long,
            attendance.clock_out_lat, attendance.clock_out_long
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
        return redirect("dashboard")


class AttendanceLogsView(LoginRequiredMixin, View):
    def get(self, request):
        logs = Attendance.objects.filter(user=request.user)

        return render(request, "attendance/logs.html", {
            "logs": logs
        })
