from django.http import JsonResponse
from django.urls import reverse

def safe_reverse(name, args=None):
    try:
        return reverse(name, args=args or [])
    except:
        return '#'

def global_search(request):
    """
    Updated global search using Elasticsearch with fallback to database search
    """
    if not request.user.is_authenticated:
        return JsonResponse({'results': []})

    user = request.user
    is_admin = user.is_superuser or user.groups.filter(name='ADMIN').exists()

    query = request.GET.get('q', '').strip()
    results = []

    if len(query) >= 2:  # Reduced from 4 to 2 for better UX
        try:
            # Import here to avoid any caching issues
            from home.search_service import search_service
            
            # Use the new Elasticsearch search service with user permissions
            search_results = search_service.global_search(query, user)
            
            # Convert Elasticsearch results to the expected format for the frontend
            
            # 1. Process Clients
            for client in search_results['clients']:
                results.append({
                    'type': 'Client',
                    'title': client['client_name'],
                    'subtitle': f"PAN: {client['pan_no']} | Email: {client['email']}",
                    'url': safe_reverse('client_details', args=[client['id']]),
                    'icon': 'bi bi-person-fill'
                })

            # 2. Process Tasks
            for task in search_results['tasks']:
                results.append({
                    'type': 'Task',
                    'title': task['task_title'],
                    'subtitle': f"Client: {task['client_name']} | Status: {task['status']}",
                    'url': safe_reverse('task_detail', args=[task['id']]),
                    'icon': 'bi bi-card-checklist'
                })

            # 3. Process Invoices
            for invoice in search_results['invoices']:
                results.append({
                    'type': 'Invoice',
                    'title': f"Inv #{invoice['id']}: {invoice['subject']}",
                    'subtitle': f"Client: {invoice['client_name']} | Status: {invoice['invoice_status']}",
                    'url': safe_reverse('invoice_list'),
                    'icon': 'bi bi-file-earmark-medical'
                })

            # 4. Process GST Details
            for gst in search_results['gst_details']:
                results.append({
                    'type': 'GST Details',
                    'title': f"GST: {gst['gst_number']}",
                    'subtitle': f"Client: {gst['client_name']} | State: {gst['state']}",
                    'url': safe_reverse('client_details', args=[gst['id']]),  # Assuming GST links to client
                    'icon': 'bi bi-file-earmark-text'
                })

            # 5. Process Leads
            for lead in search_results['leads']:
                results.append({
                    'type': 'Lead',
                    'title': lead['lead_name'],
                    'subtitle': f"Email: {lead['email']} | Phone: {lead['phone_number']}",
                    'url': safe_reverse('lead_detail', args=[lead['id']]),
                    'icon': 'bi bi-funnel'
                })

            # 6. Process Employees (only for admins)
            if is_admin:
                for employee in search_results['employees']:
                    results.append({
                        'type': 'Employee',
                        'title': employee['username'],
                        'subtitle': f"Designation: {employee['designation']} | Phone: {employee['personal_phone']}",
                        'url': '#',  # Add employee detail URL if available
                        'icon': 'bi bi-person-badge'
                    })

        except Exception as e:
            # If search fails, return error in results
            results.append({
                'type': 'Error',
                'title': 'Search Error',
                'subtitle': f'Search failed: {str(e)}',
                'url': '#',
                'icon': 'bi bi-exclamation-triangle'
            })

        # Add navigation items if they match the query
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

        # Sort results by priority
        PRIORITY = {
            'Navigation': 0,
            'Client': 1,
            'Task': 2,
            'Lead': 3,
            'Invoice': 4,
            'GST Details': 5,
            'Employee': 6,
            'Error': 99,
        }

        results.sort(key=lambda r: PRIORITY.get(r['type'], 99))
        
        # Limit results
        MAX_RESULTS = 30
        results = results[:MAX_RESULTS]

    return JsonResponse({
        'results': results,
        'elasticsearch_used': getattr(search_service, 'es_available', False) if 'search_service' in locals() else False,
        'total_count': len(results)
    })