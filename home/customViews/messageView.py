from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Value, CharField
from django.db.models.functions import Concat, Coalesce
from django.shortcuts import render, get_object_or_404, redirect
from home.models import Message
from home.forms import MessageForm
from django.conf import settings 
from cryptography.fernet import Fernet 
@login_required
def chat_view(request, user_id=None,):
    '''Calculated recent users,target users,
     form,messages,all users'''

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
            Q(sender=target_user, receiver=request.user),
        ).order_by('timestamp')

       


        


        #filtering for notifications
        Message.objects.filter(
            sender=target_user,
            receiver=request.user,
            is_seen=False
        ).update(is_seen=True)
        
        f = Fernet(settings.ENCRYPTION_KEY)
       
        if request.method == 'POST':
            form = MessageForm(request.POST)

            if form.is_valid():
                msg = form.save(commit=False)
                message_original = form.cleaned_data['content']
                message_bytes = message_original.encode('utf-8')
                message_encrypted = f.encrypt(message_bytes)
                message_decoded = message_encrypted.decode('utf-8')
                msg.content = message_decoded


                msg.sender = request.user
                msg.receiver = target_user
                msg.status = 'draft' if 'save_draft' in request.POST else 'sent'
                msg.save()
                return redirect('chat_with_user', user_id=user_id)

    # -------------------------------
    # 4. RENDER
    # -------------------------------
       
    path = request.path  
    parts = path.strip("/").split("/")  
    
    user_id = None
    if len(parts) > 1:
        user_id = parts[1]  
        user_id = int(user_id)

    return render(
        request,
        'home/chat_portal.html',
        {
            'active_users': recent_users,
            'all_users': all_users,
            'target_user': target_user,
            'messages': messages,
            'form': form,
            'user_id':user_id,
            
            
        }
    )