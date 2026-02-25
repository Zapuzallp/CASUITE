import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

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
        user = request.user
        today = timezone.now().date()
        logs = Attendance.objects.filter(user=user).order_by('-date')

        # 1. Stats Bar Logic (Current Month)
        first_of_month = today.replace(day=1)
        month_logs = logs.filter(date__gte=first_of_month)

        full_days = month_logs.filter(status='full_day').count()
        half_days = month_logs.filter(status='half_day').count()

        # Calculate Average Hours (Handling DurationField)
        avg_duration = month_logs.exclude(duration=None).aggregate(Avg('duration'))['duration__avg']
        avg_hours = round(avg_duration.total_seconds() / 3600, 1) if avg_duration else 0

        # 2. Weekly Chart Data (Last 7 Days)
        weekly_labels = []
        weekly_values = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            weekly_labels.append(day.strftime('%a'))

            day_log = logs.filter(date=day).first()
            if day_log and day_log.duration:
                hours = round(day_log.duration.total_seconds() / 3600, 1)
                weekly_values.append(hours)
            else:
                weekly_values.append(0)

        # 3. Monthly Distribution Data
        dist_data = month_logs.values('status').annotate(count=Count('id'))
        # Map DB status to Display Names and Colors
        status_map = {
            'full_day': 'Full Day',
            'half_day': 'Half Day',
            'pending': 'Pending',
            'approved': 'Present',
            'rejected': 'Rejected'
        }
        monthly_dist = []
        for item in dist_data:
            monthly_dist.append({
                'name': status_map.get(item['status'], item['status']),
                'value': item['count']
            })

        context = {
            "logs": logs,
            "today": today,
            "stats": {
                "total_entries": month_logs.count(),
                "full_days": full_days,
                "half_days": half_days,
                "avg_hours": avg_hours
            },
            "chart_data": {
                "weekly_labels": json.dumps(weekly_labels),
                "weekly_values": json.dumps(weekly_values),
                "monthly_dist": json.dumps(monthly_dist)
            }
        }
        return render(request, "attendance/logs.html", context)