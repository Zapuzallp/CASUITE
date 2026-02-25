from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from datetime import datetime, date, timedelta
import calendar
from django.contrib import messages

from home.models import Attendance, OfficeDetails, Leave


class AdminAttendanceReportView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "admin_reports/attendance_report.html"

    def test_func(self):
        user = self.request.user
        # Allow superuser, admin, partner, and branch manager
        return user.is_superuser or (
            hasattr(user, 'employee') and user.employee.role in ['ADMIN', 'PARTNER', 'BRANCH_MANAGER']
        )

    def get(self, request):
        # Filter employees based on role
        user = request.user
        if user.is_superuser or (hasattr(user, 'employee') and user.employee.role in ['ADMIN', 'PARTNER']):
            # Superuser, Admin, and Partner can see all employees
            employees = User.objects.filter(is_active=True, is_staff=True)
        elif hasattr(user, 'employee') and user.employee.role == 'BRANCH_MANAGER':
            # Branch Manager can only see employees in their branch
            branch_manager_office = user.employee.office_location
            if branch_manager_office:
                employees = User.objects.filter(
                    is_active=True, 
                    is_staff=True,
                    employee__office_location=branch_manager_office
                )
            else:
                employees = User.objects.none()
        else:
            employees = User.objects.none()
        
        offices = OfficeDetails.objects.all()

        months = [
            (1, "January"), (2, "February"), (3, "March"),
            (4, "April"), (5, "May"), (6, "June"),
            (7, "July"), (8, "August"), (9, "September"),
            (10, "October"), (11, "November"), (12, "December"),
        ]
        years = list(range(2026, 2031))

        # Filters
        employee_id = request.GET.get("employee")
        month = request.GET.get("month")
        year = request.GET.get("year")
        office_id = request.GET.get("office")
        status_filter = request.GET.get("status")

        # Default to today's records for initial load
        today = date.today()
        records = Attendance.objects.select_related("user").filter(date=today)

        # Apply filters if provided
        if employee_id or month or year or office_id or status_filter:
            records = Attendance.objects.select_related("user").all()

            if employee_id:
                records = records.filter(user__id=employee_id)

            if month and year:
                records = records.filter(
                    date__month=int(month),
                    date__year=int(year)
                )

        if office_id:
            try:
                office_id = int(office_id)
                records = records.filter(user__employee__office_location__id=office_id)
            except (ValueError, TypeError):
                # If office_id is not a number, try filtering by office name
                records = records.filter(user__employee__office_location__office_name=office_id)
            
        if status_filter:
            records = records.filter(status=status_filter)

        # Generate daily attendance data
        daily_attendance_data = []
        calendar_days = []
        total_sundays = 0
        total_holidays = 0

        if month and year:
            month_int = int(month)
            year_int = int(year)

            # Get days in month
            days_in_month = calendar.monthrange(year_int, month_int)[1]
            calendar_days = list(range(1, days_in_month + 1))

            # Count Sundays
            for day in calendar_days:
                if date(year_int, month_int, day).weekday() == 6:  # Sunday
                    total_sundays += 1

            # Generate data for each employee
            for emp in employees:
                if employee_id and str(emp.id) != employee_id:
                    continue
                
                # Filter by office if specified
                if office_id:
                    try:
                        employee_profile = emp.employee
                        if not employee_profile.office_location:
                            continue
                        
                        try:
                            office_id_int = int(office_id)
                            if employee_profile.office_location.id != office_id_int:
                                continue
                        except (ValueError, TypeError):
                            if employee_profile.office_location.office_name != office_id:
                                continue
                    except Exception:
                        continue
                
                # Get employee's shift to check days_off
                from home.models import EmployeeShift
                from django.db.models import Q
                
                # Get shift valid for the month being viewed
                month_start = date(year_int, month_int, 1)
                month_end = date(year_int, month_int, days_in_month)
                
                employee_shift = EmployeeShift.objects.filter(
                    user=emp,
                    valid_from__lte=month_end
                ).filter(
                    Q(valid_to__isnull=True) | Q(valid_to__gte=month_start)
                ).first()
                
                days_off_list = []
                if employee_shift and employee_shift.shift.days_off:
                    days_off_str = employee_shift.shift.days_off
                    # Map day abbreviations to weekday numbers
                    day_map = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
                    for day_abbr in days_off_str.split(','):
                        day_abbr = day_abbr.strip()
                        if day_abbr in day_map:
                            days_off_list.append(day_map[day_abbr])
                else:
                    # Default: Saturday and Sunday if no shift assigned
                    days_off_list = [5, 6]  # Sat=5, Sun=6
                    
                daily_status = []
                total_present = 0
                total_days_till_today = 0
                total_week_offs = 0
                total_leaves = 0
                
                # Only count days up to today if viewing current month
                today = date.today()
                max_day = days_in_month
                if year_int == today.year and month_int == today.month:
                    max_day = today.day
                
                for day in calendar_days:
                    current_date = date(year_int, month_int, day)
                    
                    # Only process days up to today for current month
                    if day <= max_day:
                        total_days_till_today += 1
                    
                    # Check if it's a day off according to shift
                    if current_date.weekday() in days_off_list:
                        daily_status.append('sunday')
                        if day <= max_day:
                            total_week_offs += 1
                        continue
                    
                    # Check for approved leave
                    try:
                        leave = Leave.objects.filter(
                            employee__user=emp,
                            status='approved',
                            start_date__lte=current_date,
                            end_date__gte=current_date
                        ).first()
                        
                        if leave:
                            daily_status.append('leave')
                            if day <= max_day:
                                total_leaves += 1
                            continue
                    except Exception:
                        pass
                    
                    # Check attendance
                    try:
                        attendance = Attendance.objects.get(
                            user=emp,
                            date=current_date
                        )
                        
                        if attendance.status == 'rejected':
                            daily_status.append('absent')
                        elif attendance.status in ['approved', 'full_day']:
                            daily_status.append('present')
                            if day <= max_day:
                                total_present += 1
                        elif attendance.status == 'half_day':
                            daily_status.append('half_day')
                            if day <= max_day:
                                total_present += 0.5
                        else:  # pending
                            daily_status.append('pending')
                    except Attendance.DoesNotExist:
                        daily_status.append('absent')
                
                # Calculate absent: Total days till today - (present + week offs + leaves)
                total_absent = total_days_till_today - (total_present + total_week_offs + total_leaves)
                total_absent = max(0, total_absent)  # Ensure non-negative

                daily_attendance_data.append({
                    'employee': emp.username,
                    'daily_status': daily_status,
                    'total_present': int(total_present) if total_present == int(total_present) else total_present,
                    'total_absent': int(total_absent),
                    'total_leaves': int(total_leaves)
                })

        # Status choices for filter
        status_choices = [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('half_day', 'Half Day Present'),
            ('full_day', 'Full Day Present')
        ]

        context = {
            "employees": employees,
            "offices": offices,
            "months": months,
            "years": years,
            "records": records,
            "daily_attendance_data": daily_attendance_data,
            "calendar_days": calendar_days,
            "total_sundays": total_sundays,
            "total_holidays": total_holidays,
            "month": month,
            "year": year,
            "status_choices": status_choices,
            "today": today.isoformat(),
            "employee_id": employee_id,
        }

        return render(request, self.template_name, context)

    def post(self, request):
        action_type = request.POST.get('action_type')
        selected_records = request.POST.getlist('selected_records')

        if not selected_records:
            messages.error(request, 'Please select records.')
            return redirect(request.get_full_path())
        
        # Filter records based on role for branch manager only
        user = request.user
        if hasattr(user, 'employee') and user.employee.role == 'BRANCH_MANAGER':
            branch_manager_office = user.employee.office_location
            if branch_manager_office:
                # Only allow updating records for employees in their branch
                allowed_records = Attendance.objects.filter(
                    id__in=selected_records,
                    user__employee__office_location=branch_manager_office
                ).values_list('id', flat=True)
                selected_records = [str(record_id) for record_id in allowed_records]
                
                if not selected_records:
                    messages.error(request, 'You can only update attendance for employees in your branch.')
                    return redirect(request.get_full_path())

        if action_type == 'clock_out_shift':
            # Handle clock out with shift time
            from django.utils import timezone
            from datetime import datetime
            from home.models import EmployeeShift, Shift
            from django.db.models import Q

            success_count = 0
            error_count = 0
            errors = []

            for record_id in selected_records:
                try:
                    attendance = Attendance.objects.get(id=record_id)

                    # Get employee shift for the date
                    employee_shift = EmployeeShift.objects.filter(
                        user=attendance.user,
                        valid_from__lte=attendance.date,
                    ).filter(
                        Q(valid_to__isnull=True) | Q(valid_to__gte=attendance.date)
                    ).first()

                    if employee_shift:
                        shift_end_time = employee_shift.shift.shift_end_time
                    else:
                        # Get default shift
                        default_shift = Shift.objects.filter(is_default=True).first()
                        if not default_shift:
                            errors.append(f"{attendance.user.username} ({attendance.date}): No shift assigned and no default shift configured")
                            error_count += 1
                            continue
                        shift_end_time = default_shift.shift_end_time

                    # Set clock_out to shift end time
                    clock_out_datetime = timezone.make_aware(
                        datetime.combine(attendance.date, shift_end_time)
                    )

                    # Handle night shifts
                    if attendance.clock_in and clock_out_datetime < attendance.clock_in:
                        clock_out_datetime += timedelta(days=1)

                    attendance.clock_out = clock_out_datetime

                    # Append remark
                    new_remark = "Auto out (shift time)"

                    if attendance.remark:
                        attendance.remark = f"{attendance.remark} | {new_remark}"
                    else:
                        attendance.remark = new_remark

                    attendance._skip_auto_status = True
                    attendance.save()
                    success_count += 1

                except Attendance.DoesNotExist:
                    errors.append(f"Record ID {record_id}: Not found")
                    error_count += 1
                except Exception as e:
                    errors.append(f"Record ID {record_id}: {str(e)}")
                    error_count += 1

            if success_count > 0:
                messages.success(request, f"Successfully updated {success_count} attendance record(s)")
            if error_count > 0:
                messages.error(request, f"Failed to update {error_count} record(s)")
                for error in errors[:5]:  # Show first 5 errors
                    messages.warning(request, error)

        elif action_type == 'status':
            # Handle bulk status update
            new_status = request.POST.get('bulk_status')
            if new_status:
                updated_count = Attendance.objects.filter(
                    id__in=selected_records
                ).update(status=new_status)
                messages.success(request, f'Successfully updated {updated_count} attendance records to {new_status}.')
            else:
                messages.error(request, 'Please select a status to update.')
        else:
            messages.error(request, 'Invalid action type.')

        return redirect(request.get_full_path())
