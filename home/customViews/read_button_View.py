from django.http import JsonResponse
from django.views.decorators.http import require_POST
from home.models import Notification, Leave

@require_POST
def mark_all_as_read(request):
    if request.user.is_authenticated:
        # 1. Update standard notifications
        Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).update(is_read=True)
        
        # 2. Update Leave records using the exact same logic as your context processor
        Leave.objects.filter(
            employee=request.user.employee,
            status__in=['approved', 'rejected'],
            readed=False
        ).update(readed=True)
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=401)