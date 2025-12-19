from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import date, datetime, time

from home.models import Attendance

from math import radians, cos, sin, asin, sqrt

def get_distance(lat1, lon1, lat2, lon2):
    # Haversine formula
    R = 6371000  # meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

class ClockInView(LoginRequiredMixin, View):
    def post(self, request):
        today = date.today()

        attendance, created = Attendance.objects.get_or_create(
            user=request.user,
            date=today
        )

        if not attendance.clock_in:
            lat = request.POST.get("lat")
            long = request.POST.get("long")
            location_name = request.POST.get("location_name")

            attendance.clock_in = timezone.now()
            attendance.clock_in_lat = lat
            attendance.clock_in_long = long
            attendance.location_name = location_name
            attendance.save()

        return redirect("dashboard")


SHIFT_END = time(22, 0)  # This can later come from settings or DB

class ClockOutView(LoginRequiredMixin, View):
    def post(self, request):
        lat = request.POST.get("lat")
        long = request.POST.get("long")

        # Get last open attendance
        attendance = Attendance.objects.filter(
            user=request.user,
            clock_in__isnull=False,
            clock_out__isnull=True
        ).order_by("-date").first()

        if not attendance:
            return redirect("dashboard")

        now = timezone.now()

        # Forgot to clock out (different day)
        if now.date() > attendance.date:
            attendance.clock_out = timezone.make_aware(
                datetime.combine(attendance.date, SHIFT_END)
            )
            attendance.remark = "Auto clock-out (forgot to clock out)"
            attendance.requires_approval = True
        else:
            attendance.clock_out = now

        # Save clock-out location
        attendance.clock_out_lat = lat
        attendance.clock_out_long = long

        # 📏 Distance validation (PM requirement)
        if (
            attendance.clock_in_lat
            and attendance.clock_in_long
            and attendance.clock_out_lat
            and attendance.clock_out_long
        ):
            distance = get_distance(
                float(attendance.clock_in_lat),
                float(attendance.clock_in_long),
                float(attendance.clock_out_lat),
                float(attendance.clock_out_long),
            )

            if distance > 100:
                attendance.requires_approval = True

                if attendance.remark:
                    attendance.remark += f" | Location mismatch ({int(distance)}m)"
                else:
                    attendance.remark = f"Location mismatch ({int(distance)}m)"

        attendance.save()
        return redirect("dashboard")

class AttendanceLogsView(LoginRequiredMixin, View):
    def get(self, request):
        logs = Attendance.objects.filter(user=request.user)

        return render(request, "attendance/logs.html", {
            "logs": logs
        })
