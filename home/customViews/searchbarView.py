from django.http import JsonResponse
from django.db.models import Q as DjangoQ
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

# Import Elasticsearch search functions
try:
    from elasticsearch_dsl import Q as ElasticsearchQ
    from home.documents import (
        ClientDocument, GSTDetailsDocument, TaskDocument,
        InvoiceDocument, EmployeeDocument, LeadDocument
    )

    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False


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

    if len(query) >= 2:  # Reduced from 4 to 2 for better UX
        if ELASTICSEARCH_AVAILABLE:
            # Use Elasticsearch for search
            try:
                results = elasticsearch_search(query, is_admin, request.user)
                # If Elasticsearch returns no results for partial queries, try database fallback
                if not results and len(query) >= 2:
                    print(f"Elasticsearch returned no results for '{query}', trying database fallback...")
                    results = database_search(query, is_admin, request.user)
            except Exception as e:
                print(f"Elasticsearch search failed: {e}")
                results = database_search(query, is_admin, request.user)
        else:
            # Fallback to database search
            results = database_search(query, is_admin, request.user)

    return JsonResponse({'results': results})


def elasticsearch_search(query, is_admin, user):
    """Search using Elasticsearch"""
    results = []

    try:
        # Search clients
        client_results = search_clients(query)
        for c in client_results[:5]:
            results.append({
                'type': 'Client',
                'title': c['client_name'],
                'subtitle': f"PAN: {c['pan_no']} | Email: {c['email']}",
                'url': reverse('client_details', args=[c['id']]),
                'icon': 'bi bi-person-fill'
            })

        # Search tasks
        task_results = search_tasks(query)
        for t in task_results[:5]:
            results.append({
                'type': 'Task',
                'title': t['task_title'],
                'subtitle': f"Client: {t['client_name']} | Status: {t['status']}",
                'url': reverse('task_detail', args=[t['id']]),
                'icon': 'bi bi-card-checklist'
            })

        # Search invoices
        invoice_results = search_invoices(query)
        for i in invoice_results[:5]:
            results.append({
                'type': 'Invoice',
                'title': f"Inv #{i['id']}: {i['subject']}",
                'subtitle': f"Client: {i['client_name']} | Status: {i['invoice_status']}",
                'url': reverse('invoice_list'),
                'icon': 'bi bi-file-earmark-medical'
            })

        # Search employees (admin only)
        if is_admin:
            employee_results = search_employees(query)
            for e in employee_results[:5]:
                results.append({
                    'type': 'Employee',
                    'title': e['full_name'],
                    'subtitle': f"Role: {e['role']} | {e.get('designation', '')}",
                    'url': reverse('employee_detail', args=[e['id']]),
                    'icon': 'bi bi-person-badge'
                })

        # Search leads
        lead_results = search_leads(query)
        for l in lead_results[:5]:
            results.append({
                'type': 'Lead',
                'title': l['lead_name'],
                'subtitle': f"Email: {l.get('email', 'N/A')} | Phone: {l['phone_number']}",
                'url': reverse('lead_detail', args=[l['id']]),
                'icon': 'bi bi-funnel'
            })

        # Search GST details
        gst_results = search_gst_details(query)
        for g in gst_results[:3]:
            results.append({
                'type': 'GST Details',
                'title': f"GST: {g['gst_number']}",
                'subtitle': f"Client: {g['client_name']} | Status: {g['status']}",
                'url': reverse('client_details', args=[g['client_id']]),
                'icon': 'bi bi-receipt'
            })

    except Exception as e:
        # If Elasticsearch fails, fallback to database search
        print(f"Elasticsearch search failed: {e}")
        return database_search(query, is_admin, user)

    # Add navigation items
    results.extend(get_navigation_matches(query))

    # Sort and limit results
    results = sort_and_limit_results(results)

    return results


def database_search(query, is_admin, user):
    """Fallback database search (original implementation)"""
    results = []

    # 1. Search Clients
    clients = Client.objects.filter(
        DjangoQ(client_name__icontains=query) |
        DjangoQ(email__icontains=query) |
        DjangoQ(pan_no__icontains=query) |
        DjangoQ(phone_number__icontains=query) |
        DjangoQ(file_number__icontains=query)
    ).distinct()[:5]
    for c in clients:
        results.append({
            'type': 'Client',
            'title': c.client_name,
            'subtitle': f"PAN: {c.pan_no} | Email: {c.email}",
            'url': reverse('client_details', args=[c.id]),
            'icon': 'bi bi-person-fill'
        })

    # 2. Search GST Details - IMPROVED
    from home.models import GSTDetails
    gst_details = GSTDetails.objects.filter(
        DjangoQ(gst_number__icontains=query) |
        DjangoQ(client__client_name__icontains=query) |
        DjangoQ(client__pan_no__icontains=query)
    ).select_related('client').distinct()[:5]

    for g in gst_details:
        results.append({
            'type': 'GST Details',
            'title': f"GST: {g.gst_number}",
            'subtitle': f"Client: {g.client.client_name} | Status: {g.status}",
            'url': reverse('client_details', args=[g.client.id]),
            'icon': 'bi bi-receipt'
        })

    # 3. Search Tasks
    tasks = Task.objects.filter(
        DjangoQ(task_title__icontains=query) | DjangoQ(description__icontains=query)
    ).distinct()[:5]
    for t in tasks:
        results.append({
            'type': 'Task',
            'title': t.task_title,
            'subtitle': f"Client: {t.client.client_name} | Status: {t.status}",
            'url': reverse('task_detail', args=[t.id]),
            'icon': 'bi bi-card-checklist'
        })

    # 4. Search Invoices
    invoices = Invoice.objects.filter(
        DjangoQ(subject__icontains=query) | DjangoQ(client__client_name__icontains=query)
    ).distinct()[:5]
    for i in invoices:
        results.append({
            'type': 'Invoice',
            'title': f"Inv #{i.id}: {i.subject}",
            'subtitle': f"Client: {i.client.client_name} | Date: {i.invoice_date.strftime('%d-%m-%Y')}",
            'url': reverse('invoice_list'),
            'icon': 'bi bi-file-earmark-medical'
        })

    # 5. For Products
    products = Product.objects.filter(
        DjangoQ(item_name__icontains=query) |
        DjangoQ(short_code__icontains=query) |
        DjangoQ(hsn_code__icontains=query)
    ).distinct()[:5]

    for p in products:
        results.append({
            'type': 'Services',
            'title': p.item_name,
            'subtitle': f"Code: {p.short_code} | HSN: {p.hsn_code}",
            'description': f"Description: {p.item_description}",
            'url': safe_reverse('list_services'),
            'icon': 'bi bi-box-seam'
        })

    # 6. For employee
    if is_admin:
        employees = Employee.objects.filter(
            DjangoQ(user__first_name__icontains=query) |
            DjangoQ(user__last_name__icontains=query) |
            DjangoQ(designation__icontains=query)
        )[:5]

        for e in employees:
            results.append({
                'type': 'Employee',
                'title': e.user.get_full_name() or e.user.username,
                'subtitle': f"Role: {e.role} | {e.designation or ''}",
                'url': reverse('employee_detail', args=[e.id]),
                'icon': 'bi bi-person-badge'
            })

    # 7. Documents
    doc_requests = DocumentRequest.objects.filter(
        DjangoQ(title__icontains=query) |
        DjangoQ(description__icontains=query)
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

    # 8. Task attributes
    extended_tasks = TaskExtendedAttributes.objects.filter(
        DjangoQ(pan_number__icontains=query) |
        DjangoQ(ack_number__icontains=query) |
        DjangoQ(arn_number__icontains=query) |
        DjangoQ(srn_number__icontains=query) |
        DjangoQ(udin_number__icontains=query) |
        DjangoQ(gstin_number__gst_number__icontains=query)  # Added GST search here too
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

    # 9. Lead
    leads = Lead.objects.filter(
        DjangoQ(lead_name__icontains=query) |
        DjangoQ(full_name__icontains=query) |
        DjangoQ(email__icontains=query) |
        DjangoQ(phone_number__icontains=query)
    )[:5]

    for l in leads:
        results.append({
            'type': 'Lead',
            'title': l.lead_name,
            'subtitle': f"Email: {l.email} | Phone: {l.phone_number}",
            'url': reverse('lead_detail', args=[l.id]),
            'icon': 'bi bi-funnel'
        })

    # 10. Search payments
    payments = Payment.objects.filter(
        DjangoQ(transaction_id__icontains=query) |
        DjangoQ(invoice__client__client_name__icontains=query)
    )[:5]

    for p in payments:
        results.append({
            'type': 'Payment',
            'title': f"Payment #{p.id}",
            'subtitle': f"Client: {p.invoice.client.client_name} | Amount: {p.amount}",
            'url': reverse('payment_detail', args=[p.id]),
            'icon': 'bi bi-currency-rupee'
        })

    # 11. Messages
    messages = Message.objects.filter(
        DjangoQ(content__icontains=query) &
        (DjangoQ(sender=user) | DjangoQ(receiver=user))
    ).distinct()[:5]

    for m in messages:
        other_user = m.receiver if m.sender == user else m.sender
        results.append({
            'type': 'Message',
            'title': f"Chat with {other_user.get_username()}",
            'subtitle': m.content[:80],
            'url': reverse('chat_with_user', args=[other_user.id]),
            'icon': 'bi bi-chat-left-text'
        })

    # Add navigation items
    results.extend(get_navigation_matches(query))

    # Sort and limit results
    results = sort_and_limit_results(results)

    return results


def get_navigation_matches(query):
    """Get matching navigation items"""
    NAV_ITEMS = [
        {'name': 'Dashboard', 'url': reverse('dashboard'), 'icon': 'bi bi-speedometer2'},
        {'name': 'All Clients', 'url': reverse('clients'), 'icon': 'bi bi-people'},
        {'name': 'All Tasks', 'url': reverse('task_list'), 'icon': 'bi bi-list-check'},
        {'name': 'All Leads', 'url': reverse('lead_list'), 'icon': 'bi bi-funnel'},
        {'name': 'All Invoices', 'url': reverse('invoice_list'), 'icon': 'bi bi-view-list'},
        {'name': 'List Services', 'url': reverse('list_services'), 'icon': 'bi bi-file-earmark-text'},
        {'name': 'List Payments', 'url': reverse('payment_list'), 'icon': 'bi bi-currency-rupee'},
    ]

    nav_results = []
    for item in NAV_ITEMS:
        if query.lower() in item['name'].lower():
            nav_results.append({
                'type': 'Navigation',
                'title': item['name'],
                'subtitle': 'Quick Access',
                'url': item['url'],
                'icon': item['icon']
            })

    return nav_results


def sort_and_limit_results(results):
    """Sort results by priority and limit total count"""
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
        'GST Details': 11,
    }

    results.sort(key=lambda r: PRIORITY.get(r['type'], 99))
    return results[:MAX_RESULTS]


# Pure Elasticsearch search functions
def search_clients(query):
    """Search in Client documents"""
    if not ELASTICSEARCH_AVAILABLE:
        return []

    search = ClientDocument.search()

    # Multi-match query across relevant fields
    q = ElasticsearchQ("multi_match",
                       query=query,
                       fields=[
                           'client_name^3',  # Boost client name
                           'primary_contact_name^2',
                           'email^2',
                           'phone_number^2',
                           'pan_no^2',
                           'file_number^2',
                           'aadhar',
                           'din_no',
                           'tan_no',
                           'father_name',
                           'address_line1',
                           'city',
                           'remarks',
                       ],
                       fuzziness='AUTO',  # Typo tolerance
                       operator='or'
                       )

    search = search.query(q)[:20]  # Limit to 20 results
    response = search.execute()

    return [
        {
            'id': hit.id,
            'client_name': hit.client_name,
            'email': hit.email,
            'phone_number': hit.phone_number,
            'pan_no': hit.pan_no,
            'file_number': getattr(hit, 'file_number', None),
            'client_type': hit.client_type,
            'status': hit.status,
            'url': f'/client/{hit.id}/',
            'type': 'client'
        }
        for hit in response
    ]


def search_gst_details(query):
    """Search in GST Details documents"""
    if not ELASTICSEARCH_AVAILABLE:
        return []

    search = GSTDetailsDocument.search()

    # Use both multi_match and wildcard queries for better partial matching
    multi_match_q = ElasticsearchQ("multi_match",
                                   query=query,
                                   fields=[
                                       'gst_number^3',  # Boost GST number
                                       'client_name^2',
                                       'client_pan^2',
                                       'registered_address',
                                       'state',
                                   ],
                                   fuzziness='AUTO',
                                   operator='or'
                                   )

    # Add wildcard query for partial GST number matching
    wildcard_q = ElasticsearchQ("wildcard", gst_number=f"*{query}*")

    # Combine both queries
    combined_q = multi_match_q | wildcard_q

    search = search.query(combined_q)[:20]
    response = search.execute()

    return [
        {
            'id': hit.id,
            'gst_number': hit.gst_number,
            'client_name': hit.client_name,
            'client_id': hit.client_id,
            'state': hit.state,
            'gst_scheme_type': hit.gst_scheme_type,
            'status': hit.status,
            'url': f'/client/{hit.client_id}/',
            'type': 'gst_detail'
        }
        for hit in response
    ]


def search_tasks(query):
    """Search in Task documents"""
    if not ELASTICSEARCH_AVAILABLE:
        return []

    search = TaskDocument.search()

    q = ElasticsearchQ("multi_match",
                       query=query,
                       fields=[
                           'task_title^3',  # Boost task title
                           'client_name^2',
                           'description^2',
                           'service_type^2',
                           'consultancy_type',
                           'status',
                           'assignee_names',
                           'created_by_name',
                       ],
                       fuzziness='AUTO',
                       operator='or'
                       )

    search = search.query(q)[:20]
    response = search.execute()

    return [
        {
            'id': hit.id,
            'task_title': hit.task_title,
            'client_name': hit.client_name,
            'client_id': hit.client_id,
            'service_type': hit.service_type,
            'status': hit.status,
            'priority': hit.priority,
            'due_date': str(hit.due_date) if hasattr(hit, 'due_date') and hit.due_date else None,
            'url': f'/task/{hit.id}/',
            'type': 'task'
        }
        for hit in response
    ]


def search_invoices(query):
    """Search in Invoice documents"""
    if not ELASTICSEARCH_AVAILABLE:
        return []

    search = InvoiceDocument.search()

    q = ElasticsearchQ("multi_match",
                       query=query,
                       fields=[
                           'invoice_number^3',  # Boost invoice number
                           'client_name^2',
                           'subject^2',
                           'invoice_status',
                       ],
                       fuzziness='AUTO',
                       operator='or'
                       )

    search = search.query(q)[:20]
    response = search.execute()

    return [
        {
            'id': hit.id,
            'invoice_number': hit.invoice_number,
            'client_name': hit.client_name,
            'client_id': hit.client_id,
            'subject': hit.subject,
            'invoice_status': hit.invoice_status,
            'due_date': str(hit.due_date) if hasattr(hit, 'due_date') and hit.due_date else None,
            'url': f'/invoice/{hit.id}/',
            'type': 'invoice'
        }
        for hit in response
    ]


def search_employees(query):
    """Search in Employee documents"""
    if not ELASTICSEARCH_AVAILABLE:
        return []

    search = EmployeeDocument.search()

    q = ElasticsearchQ("multi_match",
                       query=query,
                       fields=[
                           'full_name^3',  # Boost full name
                           'username^2',
                           'first_name^2',
                           'last_name^2',
                           'email^2',
                           'personal_email^2',
                           'personal_phone',
                           'work_phone',
                           'designation',
                           'role',
                       ],
                       fuzziness='AUTO',
                       operator='or'
                       )

    search = search.query(q)[:20]
    response = search.execute()

    return [
        {
            'id': hit.id,
            'full_name': hit.full_name,
            'username': hit.username,
            'email': hit.email,
            'designation': getattr(hit, 'designation', None),
            'role': hit.role,
            'personal_phone': getattr(hit, 'personal_phone', None),
            'url': f'/employee/{hit.id}/',
            'type': 'employee'
        }
        for hit in response
    ]


def search_leads(query):
    """Search in Lead documents"""
    if not ELASTICSEARCH_AVAILABLE:
        return []

    search = LeadDocument.search()

    q = ElasticsearchQ("multi_match",
                       query=query,
                       fields=[
                           'lead_name^3',  # Boost lead name
                           'full_name^2',
                           'email^2',
                           'phone_number^2',
                           'requirements',
                           'status',
                           'remarks',
                           'assigned_to_names',
                       ],
                       fuzziness='AUTO',
                       operator='or'
                       )

    search = search.query(q)[:20]
    response = search.execute()

    return [
        {
            'id': hit.id,
            'lead_name': hit.lead_name,
            'full_name': hit.full_name,
            'email': getattr(hit, 'email', None),
            'phone_number': hit.phone_number,
            'status': hit.status,
            'lead_value': str(getattr(hit, 'lead_value', None)) if hasattr(hit, 'lead_value') else None,
            'url': f'/lead/{hit.id}/',
            'type': 'lead'
        }
        for hit in response
    ]