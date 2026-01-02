from .models import Notification


def notifications_context(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:5]

        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return {
            "notifications": notifications,
            "unread_count": unread_count
        }

    return {
        "notifications": [],
        "unread_count": 0
    }
