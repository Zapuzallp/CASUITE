from home.models import Notification,Leave
from home.models import Message
from django.db.models import Max
from django.conf import settings 
from cryptography.fernet import Fernet 


def notifications_context(request):
    """
    Context processor to provide notification and leave-related data for templates.

    This function retrieves the latest unread notifications for the authenticated user,
    along with recent leave status updates (approved or rejected). It also calculates
    the total count of unread notifications and leave updates.

    Parameters:
    ----------
    request : HttpRequest
        The incoming HTTP request object containing user information.

    Returns:
    -------
    dict
        A dictionary containing:
        - notifications : QuerySet
            Latest 5 unread notifications for the authenticated user.
        - unread_count : int
            Total number of unread notifications.
        - leaves : QuerySet
            Latest 5 leave records with status 'approved' or 'rejected'.
        - total : int
            Combined count of unread notifications and leave records.
    """
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:5]
        

        leaves = Leave.objects.filter(status__in = ['approved','rejected'],readed = False, employee = request.user.employee).order_by('-created_at')
        
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        total = unread_count + leaves.count()
    else:
        notifications = []
        unread_count = 0
        leaves = []
        total = 0
    
    return {
        "notifications": notifications,
        "unread_count": unread_count,
        'leaves':leaves,
        'total':total,
    }

# header_data for notification messages
def header_data(request):
    """
    Retrieves and decrypts the latest unseen messages for the authenticated user.

    This function fetches the most recent notification from each unique sender, 
    decrypts the content using Fernet encryption, and returns them for use 
    in the header notification dropdown.

    Args:
        request: The Django HttpRequest object.

    Returns:
        dict: A dictionary containing 'header_messages' (QuerySet of Message objects).
              Returns an empty dict inside the key if the user is not authenticated.

    Raises:
        Exception: If the decryption process fails for any message.
    
    """
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
        
        for h in header_messages:
            try:
                h.content = fernet.decrypt(h.content.encode()).decode()
            except Exception:
                raise Exception  

        return {
            "header_messages": header_messages
        }
    return {"header_messages":{},}
