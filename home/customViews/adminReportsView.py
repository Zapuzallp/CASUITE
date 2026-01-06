from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from datetime import datetime, date
import calendar
from django.contrib import messages
from django.http import JsonResponse

from home.models import Attendance, OfficeDetails


class AdminAttendanceReportView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "admin_reports/attendance_report.html"

    # Only Superadmin
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        employees = User.objects.filter(is_active=True, is_staff=True)
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

        records = Attendance.objects.select_related("user").all()

        if employee_id:
            records = records.filter(user__id=employee_id)

        if month and year:
            records = records.filter(
                date__month=int(month),
                date__year=int(year)
            )

        if office_id:
            records = records.filter(location_name__icontains=office_id)
            
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
                    
                daily_status = []
                for day in calendar_days:
                    try:
                        attendance = Attendance.objects.get(
                            user=emp, 
                            date=date(year_int, month_int, day)
                        )
                        # Check status first, then clock in/out
                        if attendance.status == 'rejected':
                            daily_status.append('absent')
                        elif attendance.status == 'approved':
                            if attendance.clock_in and attendance.clock_out:
                                daily_status.append('present')
                            elif attendance.clock_in:
                                daily_status.append('half_day')
                            else:
                                daily_status.append('absent')
                        else:  # pending
                            daily_status.append('pending')
                    except Attendance.DoesNotExist:
                        # Check if Sunday
                        if date(year_int, month_int, day).weekday() == 6:
                            daily_status.append('sunday')
                        else:
                            daily_status.append('absent')
                
                daily_attendance_data.append({
                    'employee': emp.username,
                    'daily_status': daily_status
                })

        # Status choices for filter
        status_choices = [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
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
        }

        return render(request, self.template_name, context)
    
    def post(self, request):
        # Handle bulk status update
        selected_records = request.POST.getlist('selected_records')
        new_status = request.POST.get('bulk_status')
        
        if selected_records and new_status:
            updated_count = Attendance.objects.filter(
                id__in=selected_records
            ).update(status=new_status)
            
            messages.success(request, f'Successfully updated {updated_count} attendance records to {new_status}.')
        else:
            messages.error(request, 'Please select records and status to update.')
            
        return redirect(request.get_full_path())