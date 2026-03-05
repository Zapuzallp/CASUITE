from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
from home.models import (
    Client,
    Task,
    Invoice,
    Product,
    Employee,
    DocumentRequest,
    TaskExtendedAttributes,
    Message,
    Lead,
    Payment,
)

def safe_reverse(name, args=None):
    try:
        return reverse(name, args=args or [])
    except:
        return '#'



def global_search(request):
    if not request.user.is_authenticated:
        return JsonResponse({'results': []})

    user = request.user
    is_admin = user.is_superuser or user.groups.filter(name='ADMIN').exists()

    query = request.GET.get('q', '').strip()
    results = []

    if len(query) >= 4:
        # 1. Search Clients
        clients = Client.objects.filter(
            Q(client_name__icontains=query) | Q(email__icontains=query)
        ).distinct()[:5]
        for c in clients:
            results.append({
                'type': 'Client',
                'title': c.client_name,
                'subtitle': f"PAN: {c.pan_no} | Email: {c.email}",
                'url': reverse('client_details', args=[c.id]),
                'icon': 'bi bi-person-fill'
            })

        # 2. Search Tasks
        tasks = Task.objects.filter(
            Q(task_title__icontains=query) | Q(description__icontains=query)
        ).distinct()[:5]
        for t in tasks:
            results.append({
                'type': 'Task',
                'title': t.task_title,
                'subtitle': f"Client: {t.client.client_name} | Status: {t.status}",
                'url': reverse('task_detail', args=[t.id]),
                'icon': 'bi bi-card-checklist'
            })

        # 3. Search Invoices
        invoices = Invoice.objects.filter(
            Q(subject__icontains=query) | Q(client__client_name__icontains=query)
        ).distinct()[:5]
        for i in invoices:
            results.append({
                'type': 'Invoice',
                'title': f"Inv #{i.id}: {i.subject}",
                'subtitle': f"Client: {i.client.client_name} | Date: {i.invoice_date.strftime('%d-%m-%Y')}",
                'url': reverse('invoice_list'),
                'icon': 'bi bi-file-earmark-medical'
            })

        #4. For Products

        products = Product.objects.filter(
            Q(item_name__icontains=query) |
            Q(short_code__icontains=query) |
            Q(hsn_code__icontains=query)

        ).distinct()[:5]

        for p in products:
            results.append({
                'type': 'Services',
                'title': p.item_name,
                'subtitle': f"Code: {p.short_code} | HSN: {p.hsn_code}",
                'description': f"Description: {p.item_description}",
                'url': safe_reverse('list_services'), # or product detail if exists
                'icon': 'bi bi-box-seam'
            })

        #5. for employee
        if is_admin:
            employees = Employee.objects.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(designation__icontains=query)
            )[:5]

            for e in employees:
                results.append({
                    'type': 'Employee',
                    'title': e.user.get_full_name() or e.user.username,
                    'subtitle': f"Role: {e.role} | {e.designation or ''}",
                    'url': reverse('employee_detail', args=[e.id]),
                    'icon': 'bi bi-person-badge'
                })

        #6. documents

        doc_requests = DocumentRequest.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).distinct()[:5]

        for d in doc_requests:
            results.append({
                'type': 'Document Request',
                'title': d.title,
                'subtitle': f"Client: {d.client.client_name} | Due: {d.due_date}",
                'description': f"Description: {d.description}",
                'url': safe_reverse('document_request_detail', args=[d.id]),
                'icon': 'bi bi-folder2-open'
            })


        #7. Task attributes

        extended_tasks = TaskExtendedAttributes.objects.filter(
            Q(pan_number__icontains=query) |
            Q(ack_number__icontains=query) |
            Q(arn_number__icontains=query) |
            Q(srn_number__icontains=query) |
            Q(udin_number__icontains=query)
        ).select_related('task')[:5]

        existing_task_urls = {
            r['url'] for r in results if r['type'].startswith('Task')
        }

        for ext in extended_tasks:
            task = ext.task
            task_url = reverse('task_detail', args=[task.id])
            if task_url not in existing_task_urls:
                results.append({
                    'type': 'Task (Reference)',
                    'title': task.task_title,
                    'subtitle': f"Client: {task.client.client_name} | Ref matched",
                    'url': task_url,
                    'icon': 'bi bi-search'
                })

        #8 Lead
        leads = Lead.objects.filter(
            Q(lead_name__icontains=query) |
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone_number__icontains=query)
        )[:5]

        for l in leads:
            results.append({
                'type': 'Lead',
                'title': l.lead_name,
                'subtitle': f"Email: {l.email} | Phone: {l.phone_number}",
                'url': reverse('lead_detail', args=[l.id]),
                'icon': 'bi bi-funnel'
            })

        #9. Search payments
        payments = Payment.objects.filter(
            Q(transaction_id__icontains=query) |
            Q(invoice__client__client_name__icontains=query)
        )[:5]

        for p in payments:
            results.append({
                'type': 'Payment',
                'title': f"Payment #{p.id}",
                'subtitle': f"Client: {p.invoice.client.client_name} | Amount: {p.amount}",
                'url': reverse('payment_detail', args=[p.id]),
                'icon': 'bi bi-currency-rupee'
            })

        #10. Messages

        messages = Message.objects.filter(
            Q(content__icontains=query) &
            (Q(sender=request.user) | Q(receiver=request.user))
        ).distinct()[:5]

        for m in messages:
            other_user = m.receiver if m.sender == request.user else m.sender
            results.append({
                'type': 'Message',
                'title': f"Chat with {other_user.get_username()}",
                'subtitle': m.content[:80],
                'url': reverse('chat_with_user', args=[other_user.id]),
                'icon': 'bi bi-chat-left-text'
            })

        NAV_ITEMS = [
            {'name': 'Dashboard', 'url': reverse('dashboard'), 'icon': 'bi bi-speedometer2'},
            {'name': 'All Clients', 'url': reverse('clients'), 'icon': 'bi bi-people'},
            {'name': 'All Tasks', 'url': reverse('task_list'), 'icon': 'bi bi-list-check'},
            {'name': 'All Leads', 'url': reverse('lead_list'), 'icon': 'bi bi-funnel'},
            {'name': 'All Invoices', 'url': reverse('invoice_list'), 'icon': 'bi bi-view-list'},
            {'name': 'List Services', 'url': reverse('list_services'), 'icon': 'bi bi-file-earmark-text'},
            {'name': 'List Payments', 'url': reverse('payment_list'), 'icon': 'bi bi-currency-rupee'},
        ]

        for item in NAV_ITEMS:
            if query.lower() in item['name'].lower():
                results.append({
                    'type': 'Navigation',
                    'title': item['name'],
                    'subtitle': 'Quick Access',
                    'url': item['url'],
                    'icon': item['icon']
                })

        MAX_RESULTS = 30
        PRIORITY = {
            'Navigation': 0,
            'Client': 1,
            'Task': 2,
            'Task (Reference)': 3,
            'Lead': 4,
            'Invoice': 5,
            'Payment': 6,
            'Services': 7,
            'Employee': 8,
            'Document Request': 9,
            'Message': 10,
        }

        results.sort(key=lambda r: PRIORITY.get(r['type'], 99))
        results = results[:MAX_RESULTS]


    return JsonResponse({'results': results})