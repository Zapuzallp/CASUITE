from datetime import date
from home.models import Attendance

def attendance_context(request):
    if request.user.is_authenticated:
        attendance = Attendance.objects.filter(
            user=request.user,
            date=date.today()
        ).first()
    else:
        attendance = None

    return {
        "attendance": attendance
    }
