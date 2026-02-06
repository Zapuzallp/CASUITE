from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import date, datetime, time, timedelta
from django.contrib import messages

from home.models import Attendance, OfficeDetails, EmployeeShift, Employee

from math import radians, cos, sin, asin, sqrt


def get_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points in meters using Haversine formula.
    Coordinates are rounded to 6 decimal places to match DB precision.
    """
    # Haversine formula
    R = 6371000  # meters

    # Round to 6 decimal places to match DB storage precision
    lat1 = round(float(lat1), 6)
    lon1 = round(float(lon1), 6)
    lat2 = round(float(lat2), 6)
    lon2 = round(float(lon2), 6)

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


def check_web_attendance_compliance(user, clock_in_time, clock_out_time=None, clock_in_lat=None, clock_in_lng=None,
                                    clock_out_lat=None, clock_out_lng=None):
    """Check attendance compliance for web app"""
    issues = []

    try:
        employee = Employee.objects.get(user=user)
        office = employee.office_location

        # Get employee's shift timing - try multiple approaches
        employee_shift = None

        # First try: Get shift with no end date (valid_to is NULL)
        employee_shift = EmployeeShift.objects.filter(user=user, valid_to__isnull=True).first()

        # Second try: Get shift where today is within valid date range
        if not employee_shift:
            from django.utils import timezone
            today = timezone.now().date()
            employee_shift = EmployeeShift.objects.filter(
                user=user,
                valid_from__lte=today,
                valid_to__gte=today
            ).first()

        # Third try: Get the most recent shift (fallback)
        if not employee_shift:
            employee_shift = EmployeeShift.objects.filter(user=user).order_by('-valid_from').first()

        if not employee_shift:
            # No shift assigned - mark as pending for admin review
            # DEBUG: Check if any shifts exist for this user
            all_shifts = EmployeeShift.objects.filter(user=user)
            if all_shifts.exists():
                shift_info = ", ".join([f"{s.shift.shift_name} (valid_to: {s.valid_to})" for s in all_shifts])
                issues.append(f"No active shift found. Existing shifts: {shift_info}")
            else:
                issues.append("No shift assigned - requires admin approval")
            return issues

        shift_start = employee_shift.shift.shift_start_time
        shift_end = employee_shift.shift.shift_end_time
        # Get max allowed duration from shift (in hours)
        max_allowed_duration = employee_shift.shift.maximum_allowed_duration
        # Calculate max allowed clock-in time based on shift start + max duration
        # For example: shift starts at 12:00, max duration is 1 hour, so max clock-in is 13:00
        shift_start_late = (
                    datetime.combine(date.today(), shift_start) + timedelta(hours=float(max_allowed_duration))).time()
        # 20-minute tolerance for early departure
        tolerance_minutes = 20
        shift_end_early = (datetime.combine(date.today(), shift_end) - timedelta(minutes=tolerance_minutes)).time()

        # If no office assigned, only check for late login/logout, auto-approve otherwise
        if not office:
            # Check clock-in compliance (only late arrival)
            if clock_in_time:
                # Convert timezone-aware datetime to time for comparison
                if hasattr(clock_in_time, 'astimezone'):
                    # Convert to local timezone first
                    from django.utils import timezone as tz
                    clock_in_time_local = tz.localtime(clock_in_time)
                    clock_in_time_only = clock_in_time_local.time()
                else:
                    clock_in_time_only = clock_in_time.time()

                if clock_in_time_only > shift_start_late:
                    late_minutes = (datetime.combine(date.today(), clock_in_time_only) -
                                    datetime.combine(date.today(), shift_start)).seconds // 60
                    issues.append(f"Late arrival by {late_minutes} minutes")

            # Check clock-out compliance (only early departure)
            if clock_out_time:
                # Convert timezone-aware datetime to time for comparison
                if hasattr(clock_out_time, 'astimezone'):
                    from django.utils import timezone as tz
                    clock_out_time_local = tz.localtime(clock_out_time)
                    clock_out_time_only = clock_out_time_local.time()
                else:
                    clock_out_time_only = clock_out_time.time()

                if clock_out_time_only < shift_end_early:
                    early_minutes = (datetime.combine(date.today(), shift_end) -
                                     datetime.combine(date.today(), clock_out_time_only)).seconds // 60
                    issues.append(f"Early departure by {early_minutes} minutes")

            return issues

        # Office assigned - full compliance check
        # Check clock-in compliance
        if clock_in_time:
            # Convert timezone-aware datetime to time for comparison
            if hasattr(clock_in_time, 'astimezone'):
                from django.utils import timezone as tz
                clock_in_time_local = tz.localtime(clock_in_time)
                clock_in_time_only = clock_in_time_local.time()
            else:
                clock_in_time_only = clock_in_time.time()

            # Late arrival beyond tolerance
            if clock_in_time_only > shift_start_late:
                late_minutes = (datetime.combine(date.today(), clock_in_time_only) -
                                datetime.combine(date.today(), shift_start)).seconds // 60
                issues.append(f"Late arrival by {late_minutes} minutes")

            # Check location for clock-in (allowed within 100m radius)
            if clock_in_lat and clock_in_lng and office.latitude and office.longitude:
                try:
                    distance = get_distance(float(clock_in_lat), float(clock_in_lng), float(office.latitude),
                                            float(office.longitude))
                    if distance > 100:  # 100 meters allowed radius
                        issues.append(f"Clocked in {distance:.0f}m away from office")
                except (ValueError, TypeError) as e:
                    issues.append(f"Invalid location coordinates")

        # Check clock-out compliance
        if clock_out_time:
            # Convert timezone-aware datetime to time for comparison
            if hasattr(clock_out_time, 'astimezone'):
                from django.utils import timezone as tz
                clock_out_time_local = tz.localtime(clock_out_time)
                clock_out_time_only = clock_out_time_local.time()
            else:
                clock_out_time_only = clock_out_time.time()

            # Early departure beyond tolerance
            if clock_out_time_only < shift_end_early:
                early_minutes = (datetime.combine(date.today(), shift_end) -
                                 datetime.combine(date.today(), clock_out_time_only)).seconds // 60
                issues.append(f"Early departure by {early_minutes} minutes")

            # Check location for clock-out (allowed within 200m radius)
            if clock_out_lat and clock_out_lng and office.latitude and office.longitude:
                try:
                    distance = get_distance(float(clock_out_lat), float(clock_out_lng), float(office.latitude),
                                            float(office.longitude))
                    if distance > 200:  # 200 meters allowed radius
                        issues.append(f"Clocked out {distance:.0f}m away from office")
                except (ValueError, TypeError) as e:
                    issues.append(f"Invalid location coordinates")

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
        # Round to 6 decimal places to match DB precision
        if lat and lat.strip():
            try:
                attendance.clock_in_lat = round(float(lat), 6)
            except (ValueError, TypeError):
                attendance.clock_in_lat = None
        else:
            attendance.clock_in_lat = None

        if long and long.strip():
            try:
                attendance.clock_in_long = round(float(long), 6)
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
        # Round to 6 decimal places to match DB precision
        if lat and lat.strip():
            try:
                attendance.clock_out_lat = round(float(lat), 6)
            except (ValueError, TypeError):
                attendance.clock_out_lat = None
        else:
            attendance.clock_out_lat = None

        if long and long.strip():
            try:
                attendance.clock_out_long = round(float(long), 6)
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
        # Fix: Use clock_in_long instead of clock_in_lng (matching model field name)
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
            # Set appropriate remark based on location
            try:
                employee = Employee.objects.get(user=request.user)
                if employee.office_location and attendance.clock_in_lat and attendance.clock_in_long:
                    attendance.remark = "On-time attendance within office premises"
                else:
                    attendance.remark = "On-time attendance"
            except Employee.DoesNotExist:
                attendance.remark = "On-time attendance"
            messages.success(request, 'Clocked out successfully!')

        attendance.save()
        return redirect("dashboard")


class AttendanceLogsView(LoginRequiredMixin, View):
    def get(self, request):
        logs = Attendance.objects.filter(user=request.user)

        return render(request, "attendance/logs.html", {
            "logs": logs
        })
