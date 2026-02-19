from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from home.models import Attendance
from home.utils import process_clock_in, process_clock_out


class ClockInView(LoginRequiredMixin, View):
    def post(self, request):
        lat = request.POST.get("lat")
        long = request.POST.get("long")
        location_name = request.POST.get("location_name")

        result = process_clock_in(request.user, lat, long, location_name, device_type='web')

        if result['success']:
            messages.success(request, result['message'])
        else:
            messages.warning(request, result['message'])

        return redirect("dashboard")


class ClockOutView(LoginRequiredMixin, View):
    def post(self, request):
        lat = request.POST.get("lat")
        long = request.POST.get("long")
        location_name = request.POST.get("location_name")

        result = process_clock_out(request.user, lat, long, location_name, device_type='web')

        if result['success']:
            messages.success(request, result['message'])
        else:
            messages.error(request, result['message'])

        return redirect("dashboard")


class AttendanceLogsView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Staff can only view their own attendance logs
        """
        user = request.user

        # Check if user is staff (normal employee)
        try:
            employee = user.employee
            if employee.role == 'STAFF':
                # Staff can only see their own logs
                logs = Attendance.objects.filter(user=user)
            else:
                # Branch Manager, Admin, Superuser can see their own logs
                # (For viewing all logs, they should use the admin report)
                logs = Attendance.objects.filter(user=user)
        except Exception:
            # If no employee profile, show only their own logs
            logs = Attendance.objects.filter(user=user)

        return render(request, "attendance/logs.html", {"logs": logs})