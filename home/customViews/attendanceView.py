from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import date

from home.models import Attendance


class ClockInView(LoginRequiredMixin, View):
    def post(self, request):
        today = date.today()

        attendance, created = Attendance.objects.get_or_create(
            user=request.user,
            date=today
        )

        if not attendance.clock_in:
            attendance.clock_in = timezone.now()
            attendance.location_name = request.POST.get("location_name", "")
            attendance.save()

        return redirect("dashboard")


class ClockOutView(LoginRequiredMixin, View):
    def post(self, request):
        today = date.today()

        attendance = Attendance.objects.filter(
            user=request.user,
            date=today
        ).first()

        if attendance and attendance.clock_in and not attendance.clock_out:
            attendance.clock_out = timezone.now()
            attendance.save()

        return redirect("dashboard")


class AttendanceLogsView(LoginRequiredMixin, View):
    def get(self, request):
        logs = Attendance.objects.filter(user=request.user)

        return render(request, "attendance/logs.html", {
            "logs": logs
        })
