from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from home.models import Notification, Leave


@login_required
def dashboard(request):
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]

    return render(request, "dashboard.html", {
        "unread_count": unread_count,
        "notifications": notifications
    })

@login_required
def read_all_notifications(request):
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return redirect(request.META.get("HTTP_REFERER", "/"))

@login_required
def view_notification(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )

    # mark as read
    if not notification.is_read:
        notification.is_read = True
        notification.save()

    # redirect
    if notification.target_url:
        return redirect(notification.target_url)

    return redirect("/")

@login_required
def all_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    leaves_all = Leave.objects.filter(status__in = ['approved','rejected'], employee = request.user.employee).order_by('-created_at')
    # print(leaves)
    return render(request, "home/all_notifications.html", {
        "notifications": notifications,"leaves_all":leaves_all,
    })
