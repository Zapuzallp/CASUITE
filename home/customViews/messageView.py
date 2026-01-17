from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Value, CharField
from django.db.models.functions import Concat, Coalesce
from django.shortcuts import render, get_object_or_404, redirect

from home.models import Message
from home.forms import MessageForm


@login_required
def chat_view(request, user_id=None):

    # -------------------------------
    # 1. RECENT CHAT USERS
    # -------------------------------
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
        .annotate(
            display_name=Concat(
                Coalesce('first_name', Value('')),
                Value(' '),
                Coalesce('last_name', Value('')),
                Value(' ('),
                'username',
                Value(')'),
                output_field=CharField()
            )
        )
        .order_by('-last_login')[:8]
    )

    # -------------------------------
    # 2. ALL USERS (MODAL + SEARCH)
    # -------------------------------
    search_query = request.GET.get('search', '')

    all_users = (
        User.objects
        .exclude(id=request.user.id)
        .filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query)
        )
        .annotate(
            display_name=Concat(
                Coalesce('first_name', Value('')),
                Value(' '),
                Coalesce('last_name', Value('')),
                Value(' ('),
                'username',
                Value(')'),
                output_field=CharField()
            )
        )
    )

    # -------------------------------
    # 3. ACTIVE CHAT
    # -------------------------------
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

    # -------------------------------
    # 4. RENDER
    # -------------------------------
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
