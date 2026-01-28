from home.models import Notification
from home.models import Message
from django.db.models import Max

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
    else:
        notifications = []
        unread_count = 0

    return {
        "notifications": notifications,
        "unread_count": unread_count 
    }

# header_data for notification messages
def header_data(request):
    if request.user.is_authenticated:
        latest_message_ids = Message.objects.filter(
            receiver=request.user,
            status="sent",
            is_seen=False 
        ).values('sender').annotate(
            latest_id=Max('id')
        ).values_list('latest_id', flat=True)

        header_messages = Message.objects.filter(
            id__in=latest_message_ids
        ).order_by('-timestamp')
        
        return {
            "header_messages": header_messages
        }
    return {"header_messages":{}}
