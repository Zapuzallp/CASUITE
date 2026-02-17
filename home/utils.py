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
    - STAFF: sees only own payments
    - BRANCH_MANAGER: sees payments created by staff under them AND their own payments
    - ADMIN: sees all payments in same office
    """
    from home.models import Payment, Employee
    from django.db.models import Q

    if user.is_superuser:
        return Payment.objects.all()

    try:
        employee = user.employee
    except Employee.DoesNotExist:
        return Payment.objects.none()

    role = employee.role

    if role == 'STAFF':
        return Payment.objects.filter(created_by=user, created_by__employee__office_location=employee.office_location)

    if role == 'BRANCH_MANAGER':
        # Branch Manager sees own + staff under him

        staff_users = Employee.objects.filter(supervisor=user).values_list('user', flat=True)
        return Payment.objects.filter(
            Q(created_by=user) | Q(created_by__in=staff_users)
        )

    if role == 'ADMIN':
        # Admin can see all payments in branch
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

    # Admin can approve any payment
    if approver.role == 'ADMIN':
        return approver.office_location == creator.office_location

    # Branch manager can approve only their own payments
    if approver.role == 'BRANCH_MANAGER':
        return (
            payment.created_by == user or
            creator.supervisor == user
        )

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

    if actor.role == "ADMIN":
        return actor.office_location == creator.office_location

    if actor.role == "BRANCH_MANAGER":
        return (
            payment.created_by == user or
            creator.supervisor == user
        )

    return False

from django.db.models import Sum
from decimal import Decimal

def get_invoice_totals(invoice):
    total_amount = invoice.items.aggregate(
        total=Sum('net_total')
    )['total'] or Decimal('0.00')

    total_paid = invoice.payments.filter(
        payment_status='PAID',
        approval_status='APPROVED'
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    balance = total_amount - total_paid

    return total_amount, total_paid, balance
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

def check_attendance_compliance(user, clock_in_time, clock_out_time=None, clock_in_lat=None, clock_in_lng=None, clock_out_lat=None, clock_out_lng=None, device_type=None):
    """Check attendance compliance for both web and mobile"""
    from home.models import Employee, EmployeeShift
    
    remarks = []
    
    try:
        employee = Employee.objects.get(user=user)
        office = employee.office_location
        
        # Add device tracking remark
        if device_type and clock_in_time and not clock_out_time:
            if device_type == 'mobile':
                remarks.append("In: Mobile")
            elif device_type == 'web':
                remarks.append("In: Web")
        elif device_type and clock_out_time:
            if device_type == 'mobile':
                remarks.append("Out: Mobile")
            elif device_type == 'web':
                remarks.append("Out: Web")
        
        if not office:
            remarks.append("No office assigned")
        
        # Get employee's shift timing
        from django.db.models import Q
        today_date = date.today()
        
        employee_shift = EmployeeShift.objects.filter(
            user=user,
            valid_from__lte=today_date
        ).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gte=today_date)
        ).first()
        if not employee_shift:
            remarks.append("No shift assigned")
            
            if office and clock_in_lat and clock_in_lng and office.latitude and office.longitude:
                distance = get_distance(float(clock_in_lat), float(clock_in_lng), float(office.latitude), float(office.longitude))
                if distance > 100:
                    remarks.append(f"In: {distance:.0f}m away")
            
            if office and clock_out_lat and clock_out_lng and office.latitude and office.longitude:
                distance = get_distance(float(clock_out_lat), float(clock_out_lng), float(office.latitude), float(office.longitude))
                if distance > 100:
                    remarks.append(f"Out: {distance:.0f}m away")
            
            return remarks
        
        shift = employee_shift.shift
        shift_start = shift.shift_start_time
        shift_end = shift.shift_end_time
        
        # Use maximum_allowed_duration as late arrival buffer
        buffer_hours = float(shift.maximum_allowed_duration)
        buffer_minutes = int(buffer_hours * 60)
        
        # Handle night shifts that cross midnight
        shift_crosses_midnight = shift_end < shift_start
        
        # Calculate maximum allowed clock-in time
        if shift_crosses_midnight:
            max_clock_in_time = (datetime.combine(date.today(), shift_start) + timedelta(minutes=buffer_minutes)).time()
            shift_end_datetime = datetime.combine(date.today() + timedelta(days=1), shift_end)
            min_clock_out_time = (shift_end_datetime - timedelta(minutes=buffer_minutes)).time()
        else:
            max_clock_in_time = (datetime.combine(date.today(), shift_start) + timedelta(minutes=buffer_minutes)).time()
            min_clock_out_time = (datetime.combine(date.today(), shift_end) - timedelta(minutes=buffer_minutes)).time()
        
        # Check clock-in compliance
        if clock_in_time:
            if timezone.is_aware(clock_in_time):
                clock_in_local = timezone.localtime(clock_in_time)
            else:
                clock_in_local = clock_in_time
            
            clock_in_time_only = clock_in_local.time()
            
            if shift_crosses_midnight:
                if clock_in_time_only > shift_start:
                    late_minutes = (datetime.combine(date.today(), clock_in_time_only) - 
                                  datetime.combine(date.today(), shift_start)).seconds // 60
                    remarks.append(f"Late: {late_minutes}min")
            else:
                if clock_in_time_only > shift_start:
                    late_minutes = (datetime.combine(date.today(), clock_in_time_only) - 
                                  datetime.combine(date.today(), shift_start)).seconds // 60
                    remarks.append(f"Late: {late_minutes}min")
            
            if office and clock_in_lat and clock_in_lng and office.latitude and office.longitude:
                distance = get_distance(float(clock_in_lat), float(clock_in_lng), float(office.latitude), float(office.longitude))
                if distance > 100:
                    remarks.append(f"In: {distance:.0f}m away")
            elif office and (not office.latitude or not office.longitude):
                remarks.append("Office GPS not set")
            elif office and (not clock_in_lat or not clock_in_lng):
                remarks.append("In: No GPS data")
        
        # Check clock-out compliance
        if clock_out_time:
            if timezone.is_aware(clock_out_time):
                clock_out_local = timezone.localtime(clock_out_time)
            else:
                clock_out_local = clock_out_time
            
            clock_out_time_only = clock_out_local.time()
            
            if shift_crosses_midnight:
                if clock_out_time_only < min_clock_out_time:
                    shift_end_datetime = datetime.combine(date.today() + timedelta(days=1), shift_end)
                    clock_out_datetime = datetime.combine(date.today() + timedelta(days=1), clock_out_time_only)
                    early_minutes = (shift_end_datetime - clock_out_datetime).seconds // 60
                    remarks.append(f"Early: {early_minutes}min")
            else:
                if clock_out_time_only < min_clock_out_time:
                    early_minutes = (datetime.combine(date.today(), shift_end) - 
                                   datetime.combine(date.today(), clock_out_time_only)).seconds // 60
                    remarks.append(f"Early: {early_minutes}min")
            
            if office and clock_out_lat and clock_out_lng and office.latitude and office.longitude:
                distance = get_distance(float(clock_out_lat), float(clock_out_lng), float(office.latitude), float(office.longitude))
                if distance > 100:
                    remarks.append(f"Out: {distance:.0f}m away")
            elif office and (not office.latitude or not office.longitude):
                remarks.append("Office GPS not set")
            elif office and (not clock_out_lat or not clock_out_lng):
                remarks.append("Out: No GPS data")
    
    except Employee.DoesNotExist:
        remarks.append("No employee profile")
    
    return remarks

def process_clock_in(user, lat=None, long=None, location_name=None, device_type='web'):
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
    compliance_remarks = check_attendance_compliance(user, current_time, clock_in_lat=lat, clock_in_lng=long, device_type=device_type)
    
    if compliance_remarks:
        violation_keywords = ['late', 'away', 'early']
        has_violations = any(keyword in remark.lower() for remark in compliance_remarks for keyword in violation_keywords)
        
        new_remarks = "; ".join(compliance_remarks)
        if attendance.remark:
            attendance.remark = f"{attendance.remark}; {new_remarks}"
        else:
            attendance.remark = new_remarks
            
        if has_violations:
            attendance.status = 'pending'
            message = f"Attendance marked as pending: {'; '.join(compliance_remarks)}"
            success = False
        else:
            attendance.status = 'approved'
            message = 'Clocked in successfully!'
            success = True
    else:
        device_remark = f"In: {device_type.capitalize()}"
        if attendance.remark:
            attendance.remark = f"{attendance.remark}; {device_remark}"
        else:
            attendance.remark = device_remark
        attendance.status = 'approved'
        message = 'Clocked in successfully!'
        success = True

    attendance._skip_auto_status = True
    attendance.save()
    return {'success': success, 'message': message}

def process_clock_out(user, lat=None, long=None, location_name=None, device_type='web'):
    """Process clock out for both web and mobile"""
    from home.models import Attendance
    
    current_time = timezone.now()
    attendance = Attendance.objects.filter(user=user, clock_out__isnull=True).last()

    if not attendance:
        return {'success': False, 'message': 'No active clock-in found!'}

    auto_clocked_out = False
    # Handle forgotten clock out
    if current_time.date() > attendance.date:
        from home.models import EmployeeShift
        from django.db.models import Q
        
        today_date = attendance.date
        employee_shift = EmployeeShift.objects.filter(
            user=user,
            valid_from__lte=today_date
        ).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gte=today_date)
        ).first()
        
        if employee_shift:
            shift_end_time = employee_shift.shift.shift_end_time
            attendance.clock_out = timezone.make_aware(datetime.combine(attendance.date, shift_end_time))
            if attendance.remark:
                attendance.remark = f"{attendance.remark}; Auto out (shift time)"
            else:
                attendance.remark = "Auto out (shift time)"
        else:
            shift_end_time = time(23, 59)
            attendance.clock_out = timezone.make_aware(datetime.combine(attendance.date, shift_end_time))
            if attendance.remark:
                attendance.remark = f"{attendance.remark}; Auto out"
            else:
                attendance.remark = "Auto out"
        
        attendance.status = "pending"
        auto_clocked_out = True
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
    if not auto_clocked_out:
        compliance_remarks = check_attendance_compliance(
            user, None, attendance.clock_out,
            None, None,
            attendance.clock_out_lat, attendance.clock_out_long,
            device_type=device_type
        )
        
        if compliance_remarks:
            violation_keywords = ['late', 'away', 'early']
            has_violations = any(keyword in remark.lower() for remark in compliance_remarks for keyword in violation_keywords)
            
            new_remarks = "; ".join(compliance_remarks)
            if attendance.remark:
                attendance.remark = f"{attendance.remark}; {new_remarks}"
            else:
                attendance.remark = new_remarks
                
            if has_violations:
                attendance.status = 'pending'
                message = f"Attendance marked as pending: {'; '.join(compliance_remarks)}"
                success = False
            else:
                attendance.status = 'approved'
                message = 'Clocked out successfully!'
                success = True
        else:
            device_remark = f"Out: {device_type.capitalize()}"
            if attendance.remark:
                attendance.remark = f"{attendance.remark}; {device_remark}"
            else:
                attendance.remark = device_remark
            attendance.status = 'approved'
            message = 'Clocked out successfully!'
            success = True
    else:
        message = 'Auto clocked out due to missing clock-out'
        success = False

    attendance._skip_auto_status = True
    attendance.save()
    return {'success': success, 'message': message}

