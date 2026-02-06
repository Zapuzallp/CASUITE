def generate_file_number(office_location):
    """
    Generates a unique file number based on office location.
    Example: KO000001, KO000002
    """

    from home.models import Client

    # Office code (first 2 letters)
    office_code = office_location.office_name[:2].upper()

    # Get latest client for this office having file_number
    last_client = (
        Client.objects
        .filter(
            office_location=office_location,
            file_number__startswith=office_code
        )
        .order_by('-file_number')
        .first()
    )

    if last_client and last_client.file_number:
        # Extract numeric part
        last_number = int(last_client.file_number.replace(office_code, ''))
        next_number = last_number + 1
    else:
        # First client for this office
        next_number = 1

    return f"{office_code}{str(next_number).zfill(6)}"

def get_visible_payments(user):
    """
    Returns a queryset of payments the given user is allowed to see.
    - superuser: sees all
    - STAFF: sees only own payments (in same office)
    - ADMIN: sees payments created by staff under them AND their own payments (same office)
    - BRANCH_MANAGER: sees all payments in same office
    """
    from home.models import Payment, Employee

    if user.is_superuser:
        return Payment.objects.all()

    try:
        employee = user.employee
    except Employee.DoesNotExist:
        return Payment.objects.none()

    role = employee.role

    if role == 'STAFF':
        return Payment.objects.filter(created_by=user, created_by__employee__office_location=employee.office_location)

    if role == 'ADMIN':
        # payments created by users who report to this admin, plus admin's own payments
        staff_users = Employee.objects.filter(supervisor=user, office_location=employee.office_location).values_list('user', flat=True)
        user_list = list(staff_users) + [user]
        return Payment.objects.filter(created_by__in=user_list)

    if role == 'BRANCH_MANAGER':
        # All payments in same branch
        return Payment.objects.filter(created_by__employee__office_location=employee.office_location)

    return Payment.objects.none()

def can_approve_payment(user, payment):
    try:
        approver = user.employee
        creator = payment.created_by.employee
    except Exception:
        return False

    # Must be same branch
    if approver.office_location != creator.office_location:
        return False

    # Branch manager can approve anything in branch
    if approver.role == 'BRANCH_MANAGER':
        return True

    # Admin can approve staff under them
    if approver.role == 'ADMIN' and creator.supervisor == user:
        return True

    return False

def can_cancel_payment(user, payment):
    try:
        actor = user.employee
        creator = payment.created_by.employee
    except Exception:
        return False

    if payment.approval_status != "PENDING" or payment.payment_status != "PENDING":
        return False

    if payment.created_by == user:
        return True

    if actor.role == "ADMIN" and creator.supervisor == user and actor.office_location == creator.office_location:
        return True

    if actor.role == "BRANCH_MANAGER" and actor.office_location == creator.office_location:
        return True

    return False

# Attendance utility functions
from math import radians, cos, sin, asin, sqrt
from django.utils import timezone
from datetime import date, datetime, time, timedelta

def get_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371000  # meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def check_attendance_compliance(user, clock_in_time, clock_out_time=None, clock_in_lat=None, clock_in_lng=None, clock_out_lat=None, clock_out_lng=None):
    """Check attendance compliance for both web and mobile"""
    from home.models import Employee, EmployeeShift
    
    issues = []
    
    try:
        employee = Employee.objects.get(user=user)
        office = employee.office_location
        
        # Get employee's shift timing
        employee_shift = EmployeeShift.objects.filter(user=user, valid_to__isnull=True).first()
        if not employee_shift:
            # No shift assigned - proceed without time checks
            return issues
        
        shift = employee_shift.shift
        shift_start = shift.shift_start_time
        shift_end = shift.shift_end_time
        
        # Use fixed 20 minute buffer time
        buffer_minutes = 20
        shift_start_late = (datetime.combine(date.today(), shift_start) + timedelta(minutes=buffer_minutes)).time()
        shift_end_early = (datetime.combine(date.today(), shift_end) - timedelta(minutes=buffer_minutes)).time()
        
        # If no office assigned, only check for time violations
        if not office:
            if clock_in_time:
                clock_in_time_only = clock_in_time.time()
                if clock_in_time_only > shift_start_late:
                    late_minutes = (datetime.combine(date.today(), clock_in_time_only) - 
                                  datetime.combine(date.today(), shift_start)).seconds // 60
                    issues.append(f"Late arrival by {late_minutes} minutes")
            
            if clock_out_time:
                clock_out_time_only = clock_out_time.time()
                if clock_out_time_only < shift_end_early:
                    early_minutes = (datetime.combine(date.today(), shift_end) - 
                                   datetime.combine(date.today(), clock_out_time_only)).seconds // 60
                    issues.append(f"Early departure by {early_minutes} minutes")
            
            return issues
        
        # Office assigned - check both location and time compliance
        if clock_in_time:
            clock_in_time_only = clock_in_time.time()
            
            # Check time compliance
            if clock_in_time_only > shift_start_late:
                late_minutes = (datetime.combine(date.today(), clock_in_time_only) - 
                              datetime.combine(date.today(), shift_start)).seconds // 60
                issues.append(f"Late arrival by {late_minutes} minutes")
            
            # Check location compliance (100m radius)
            if clock_in_lat and clock_in_lng and office.latitude and office.longitude:
                distance = get_distance(float(clock_in_lat), float(clock_in_lng), float(office.latitude), float(office.longitude))
                if distance > 100:
                    issues.append(f"Clocked in {distance:.0f}m away from office")
        
        if clock_out_time:
            clock_out_time_only = clock_out_time.time()
            
            # Check time compliance
            if clock_out_time_only < shift_end_early:
                early_minutes = (datetime.combine(date.today(), shift_end) - 
                               datetime.combine(date.today(), clock_out_time_only)).seconds // 60
                issues.append(f"Early departure by {early_minutes} minutes")
            
            # Check location compliance (100m radius)
            if clock_out_lat and clock_out_lng and office.latitude and office.longitude:
                distance = get_distance(float(clock_out_lat), float(clock_out_lng), float(office.latitude), float(office.longitude))
                if distance > 100:
                    issues.append(f"Clocked out {distance:.0f}m away from office")
    
    except Employee.DoesNotExist:
        issues.append("Employee profile not found")
    
    return issues

def process_clock_in(user, lat=None, long=None, location_name=None):
    """Process clock in for both web and mobile"""
    from home.models import Attendance
    from django.contrib import messages
    
    today = date.today()
    current_time = timezone.now()

    attendance, _ = Attendance.objects.get_or_create(user=user, date=today)

    if attendance.clock_in:
        return {'success': False, 'message': 'Already clocked in today!'}

    attendance.clock_in = current_time
    
    # Set location fields
    if lat and lat.strip():
        try:
            attendance.clock_in_lat = float(lat)
        except (ValueError, TypeError):
            attendance.clock_in_lat = None
    
    if long and long.strip():
        try:
            attendance.clock_in_long = float(long)
        except (ValueError, TypeError):
            attendance.clock_in_long = None
    
    if location_name and location_name.strip():
        attendance.location_name = location_name

    # Check compliance
    compliance_issues = check_attendance_compliance(user, current_time, clock_in_lat=lat, clock_in_lng=long)
    
    if compliance_issues:
        attendance.status = 'pending'
        attendance.remark = "; ".join(compliance_issues)
        message = f"Attendance marked as pending: {'; '.join(compliance_issues)}"
        success = False
    else:
        attendance.status = 'approved'
        message = 'Clocked in successfully!'
        success = True

    attendance.save()
    return {'success': success, 'message': message}

def process_clock_out(user, lat=None, long=None, location_name=None):
    """Process clock out for both web and mobile"""
    from home.models import Attendance
    
    current_time = timezone.now()
    attendance = Attendance.objects.filter(user=user, clock_out__isnull=True).last()

    if not attendance:
        return {'success': False, 'message': 'No active clock-in found!'}

    # Handle forgotten clock out
    if current_time.date() > attendance.date:
        from home.models import EmployeeShift
        # Get user's shift end time, default to 22:00 if no shift
        employee_shift = EmployeeShift.objects.filter(user=user, valid_to__isnull=True).first()
        if employee_shift:
            shift_end_time = employee_shift.shift.shift_end_time
        else:
            shift_end_time = time(23, 59)  # Default fallback
        
        attendance.clock_out = timezone.make_aware(datetime.combine(attendance.date, shift_end_time))
        attendance.status = "pending"
        attendance.remark = "Auto clock-out (missed logout)"
    else:
        attendance.clock_out = current_time

    # Set location fields
    if lat and lat.strip():
        try:
            attendance.clock_out_lat = float(lat)
        except (ValueError, TypeError):
            attendance.clock_out_lat = None
    
    if long and long.strip():
        try:
            attendance.clock_out_long = float(long)
        except (ValueError, TypeError):
            attendance.clock_out_long = None
    
    # Set location_name if provided or generate from coordinates
    if location_name and location_name.strip():
        attendance.location_name = location_name
    elif not attendance.location_name and lat and long:
        try:
            lat_f = float(lat)
            lng_f = float(long)
            attendance.location_name = f"Location ({lat_f:.4f}, {lng_f:.4f})"
        except (ValueError, TypeError):
            pass

    # Check compliance for clock-out
    compliance_issues = check_attendance_compliance(
        user, attendance.clock_in, attendance.clock_out,
        attendance.clock_in_lat, attendance.clock_in_long,
        attendance.clock_out_lat, attendance.clock_out_long
    )
    
    if compliance_issues:
        attendance.status = 'pending'
        attendance.remark = "; ".join(compliance_issues)
        message = f"Attendance marked as pending: {'; '.join(compliance_issues)}"
        success = False
    else:
        attendance.status = 'approved'
        message = 'Clocked out successfully!'
        success = True

    attendance.save()
    return {'success': success, 'message': message}

