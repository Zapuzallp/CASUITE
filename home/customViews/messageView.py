from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db.models import Q, Max
from home.models import Message,Employee
from home.forms import MessageForm
from django.contrib.auth.decorators import login_required


@login_required
def chat_view(request, user_id=None):


    chat_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    )

    user_ids = set()
    for msg in chat_messages:
        if msg.sender_id != request.user.id:
            user_ids.add(msg.sender_id)
        if msg.receiver_id != request.user.id:
            user_ids.add(msg.receiver_id)

    recent_users = (
        User.objects
        .filter(id__in=user_ids)
        .order_by('-last_login')[:8]
    )

    # -------------------------------
    # 2. ALL USERS (Modal)
    # -------------------------------
    all_users = User.objects.exclude(id=request.user.id)


    target_user = None
    messages = None
    form = MessageForm()

    if user_id is not None:
        target_user = get_object_or_404(User, id=user_id)

        messages = Message.objects.filter(
            Q(sender=request.user, receiver=target_user) |
            Q(sender=target_user, receiver=request.user)
        ).order_by('timestamp')

        if request.method == 'POST':
            form = MessageForm(request.POST)
            if form.is_valid():
                msg = form.save(commit=False)
                msg.sender = request.user
                msg.receiver = target_user
                msg.status = 'draft' if 'save_draft' in request.POST else 'sent'
                msg.save()
                return redirect('chat_with_user', user_id=user_id)

    # ✅ RETURN IS ALWAYS EXECUTED
    return render(
        request,
        'home/chat_portal.html',
        {
            'active_users': recent_users,
            'all_users': all_users,
            'target_user': target_user,
            'messages': messages,
            'form': form,
        }
    )