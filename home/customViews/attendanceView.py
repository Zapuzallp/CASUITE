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
        
        result = process_clock_in(request.user, lat, long, location_name)
        
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
        
        result = process_clock_out(request.user, lat, long, location_name)
        
        if result['success']:
            messages.success(request, result['message'])
        else:
            messages.error(request, result['message'])
        
        return redirect("dashboard")

class AttendanceLogsView(LoginRequiredMixin, View):
    def get(self, request):
        logs = Attendance.objects.filter(user=request.user)
        return render(request, "attendance/logs.html", {"logs": logs})