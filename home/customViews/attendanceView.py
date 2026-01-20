from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import date, datetime, time

from home.models import Attendance, OfficeDetails, EmployeeShift

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

        attendance, _ = Attendance.objects.get_or_create(
            user=request.user,
            date=today
        )

        if attendance.clock_in:
            return redirect("dashboard")

        lat = request.POST.get("lat")
        long = request.POST.get("long")
        location_name = request.POST.get("location_name")

        attendance.clock_in = timezone.now()
        attendance.clock_in_lat = lat
        attendance.clock_in_long = long
        attendance.location_name = location_name

        remarks = []

        emp_shift = EmployeeShift.objects.filter(user=request.user).first()
        office = OfficeDetails.objects.first()

        # Late login
        if emp_shift:
            shift_start = emp_shift.shift.shift_start_time
            if attendance.clock_in.time() > shift_start:
                remarks.append("Late login")

        # Distance check
        if office and lat and long:
            distance = get_distance(
                float(lat),
                float(long),
                float(office.latitude),
                float(office.longitude)
            )

            if distance > 100:
                remarks.append(f"Clock-in {int(distance)}m away from office")

        # Apply remarks
        if remarks:
            attendance.status = "pending"
            attendance.remark = " || ".join(remarks)
        else:
            attendance.status = "approved"

        attendance.save()
        return redirect("dashboard")

class ClockOutView(LoginRequiredMixin, View):
    def post(self, request):
        lat = request.POST.get("lat")
        long = request.POST.get("long")

        attendance = Attendance.objects.filter(
            user=request.user,
            clock_out__isnull=True
        ).last()

        if not attendance:
            return redirect("dashboard")

        now = timezone.now()
        emp_shift = EmployeeShift.objects.filter(user=request.user).first()
        office = OfficeDetails.objects.first()

        # Handle forgotten logout
        if now.date() > attendance.date:
            attendance.clock_out = timezone.make_aware(
                datetime.combine(attendance.date, time(22, 0))
            )
            attendance.status = "pending"
            attendance.remark = "Auto clock-out (missed logout)"
        else:
            attendance.clock_out = now

        attendance.clock_out_lat = lat
        attendance.clock_out_long = long

        # Early logout
        if emp_shift:
            shift_end = emp_shift.shift.shift_end_time
            if attendance.clock_out.time() < shift_end:
                attendance.status = "pending"
                attendance.remark = "Early logout"

        # Distance check
        if office and lat and long:
            distance = get_distance(
                float(attendance.clock_in_lat),
                float(attendance.clock_in_long),
                float(lat),
                float(long),
            )

            if distance > 100:
                attendance.status = "pending"
                if attendance.remark:
                    attendance.remark += f" || Clock-out {int(distance)}m away from office"
                else:
                    attendance.remark = f"Clock-out {int(distance)}m away from office"

        attendance.save()
        return redirect("dashboard")


class AttendanceLogsView(LoginRequiredMixin, View):
    def get(self, request):
        logs = Attendance.objects.filter(user=request.user)

        return render(request, "attendance/logs.html", {
            "logs": logs
        })
