from home.models import Notification
from home.models import Message
from django.db.models import Max
from django.conf import settings 
from cryptography.fernet import Fernet 

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
    fernet = Fernet(settings.ENCRYPTION_KEY)
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
        
        # yield notifications
        def yield_notifications():
            i = 0
            while i <len(header_messages):
                yield header_messages[i]
                i+=1
        # for loop on yield notifications
        for h in yield_notifications():
            h.content = fernet.decrypt(h.content.encode()).decode()


        return {
            "header_messages": header_messages
        }
    return {"header_messages":{},}
