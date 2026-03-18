from elasticsearch_dsl import Q, Search
from elasticsearch import Elasticsearch, ConnectionError
from django.conf import settings
from django.db.models import Q as DjangoQ
from .models import Client, GSTDetails, Task, Invoice, Lead, Employee
import logging

logger = logging.getLogger(__name__)

class GlobalSearchService:
    """Service for performing global search across multiple models with permission filtering"""
    
    def __init__(self):
        self.es_available = self._check_elasticsearch_connection()
    
    def _check_elasticsearch_connection(self):
        """Check if Elasticsearch is available"""
        try:
            es = Elasticsearch([settings.ELASTICSEARCH_HOST])
            es.ping()
            return True
        except (ConnectionError, Exception) as e:
            logger.warning(f"Elasticsearch not available: {e}")
            return False
    
    def _get_user_permission_filter(self, user):
        """
        Generate Elasticsearch permission filter based on user role and permissions
        """
        if user.is_superuser:
            # Superuser can see everything - no filter needed
            return None
        
        try:
            employee = user.employee
            role = employee.role
        except:
            # User has no employee record - treat as staff with minimal access
            role = 'STAFF'
            employee = None
        
        # Build permission conditions
        permission_conditions = []
        
        # All users can see records assigned to them or created by them
        permission_conditions.extend([
            {"term": {"assigned_ca_id": user.id}},
            {"term": {"created_by_id": user.id}}
        ])
        
        # Branch managers can also see records from their office location
        if role == 'BRANCH_MANAGER' and employee and employee.office_location_id:
            permission_conditions.append({
                "term": {"office_location_id": employee.office_location_id}
            })
        
        # For leads, also check assigned_to_ids (many-to-many field)
        permission_conditions.append({
            "term": {"assigned_to_ids": user.id}
        })
        
        # Return bool should query with all permission conditions
        return {
            "bool": {
                "should": permission_conditions,
                "minimum_should_match": 1
            }
        }
    
    def global_search(self, query, user):
        """
        Perform global search across all indexed models with permission filtering
        Returns categorized results
        """
        if not query or len(query.strip()) < 2:
            return self._empty_results()
        
        if self.es_available:
            try:
                return self._elasticsearch_search(query, user)
            except Exception as e:
                logger.error(f"Elasticsearch search failed: {e}")
                # Fallback to database search
                return self._database_search(query, user)
        else:
            return self._database_search(query, user)
    
    def _elasticsearch_search(self, query, user):
        """Perform search using Elasticsearch with permission filtering"""
        results = {
            "clients": [],
            "gst_details": [],
            "tasks": [],
            "invoices": [],
            "leads": [],
            "employees": []
        }
        
        # Get permission filter for the user
        permission_filter = self._get_user_permission_filter(user)
        
        # Search clients
        client_search = Search(index='clients').query(
            "multi_match",
            query=query,
            fields=['client_name^2', 'pan_no^2', 'phone_number', 'email', 'file_number', 'city', 'state'],
            fuzziness='AUTO'
        )
        
        # Apply permission filter if needed
        if permission_filter:
            client_search = client_search.filter(permission_filter)
        
        client_search = client_search[:10]
        
        for hit in client_search.execute():
            results["clients"].append({
                'id': hit.meta.id,
                'client_name': getattr(hit, 'client_name', ''),
                'pan_no': getattr(hit, 'pan_no', ''),
                'phone_number': getattr(hit, 'phone_number', ''),
                'email': getattr(hit, 'email', ''),
                'file_number': getattr(hit, 'file_number', ''),
                'city': getattr(hit, 'city', ''),
                'state': getattr(hit, 'state', ''),
            })
        
        # Search GST Details
        gst_search = Search(index='gst_details').query(
            "multi_match",
            query=query,
            fields=['gst_number^2', 'state', 'client_name'],
            fuzziness='AUTO'
        )
        
        if permission_filter:
            gst_search = gst_search.filter(permission_filter)
        
        gst_search = gst_search[:10]
        
        for hit in gst_search.execute():
            results["gst_details"].append({
                'id': hit.meta.id,
                'gst_number': getattr(hit, 'gst_number', ''),
                'state': getattr(hit, 'state', ''),
                'client_name': getattr(hit, 'client_name', ''),
            })
        
        # Search Tasks
        task_search = Search(index='tasks').query(
            "multi_match",
            query=query,
            fields=['task_title^2', 'description', 'service_type', 'status', 'client_name'],
            fuzziness='AUTO'
        )
        
        if permission_filter:
            task_search = task_search.filter(permission_filter)
        
        task_search = task_search[:10]
        
        for hit in task_search.execute():
            results["tasks"].append({
                'id': hit.meta.id,
                'task_title': getattr(hit, 'task_title', ''),
                'description': getattr(hit, 'description', ''),
                'service_type': getattr(hit, 'service_type', ''),
                'status': getattr(hit, 'status', ''),
                'client_name': getattr(hit, 'client_name', ''),
            })
        
        # Search Invoices
        invoice_search = Search(index='invoices').query(
            "multi_match",
            query=query,
            fields=['subject^2', 'invoice_status', 'client_name'],
            fuzziness='AUTO'
        )
        
        if permission_filter:
            invoice_search = invoice_search.filter(permission_filter)
        
        invoice_search = invoice_search[:10]
        
        for hit in invoice_search.execute():
            results["invoices"].append({
                'id': hit.meta.id,
                'subject': getattr(hit, 'subject', ''),
                'invoice_status': getattr(hit, 'invoice_status', ''),
                'client_name': getattr(hit, 'client_name', ''),
            })
        
        # Search Leads
        lead_search = Search(index='leads').query(
            "multi_match",
            query=query,
            fields=['lead_name^2', 'full_name^2', 'phone_number', 'email', 'status'],
            fuzziness='AUTO'
        )
        
        # For leads, use a simpler permission filter (created_by or assigned_to)
        if not user.is_superuser:
            lead_permission_filter = {
                "bool": {
                    "should": [
                        {"term": {"created_by_id": user.id}},
                        {"term": {"assigned_to_ids": user.id}}
                    ],
                    "minimum_should_match": 1
                }
            }
            lead_search = lead_search.filter(lead_permission_filter)
        
        lead_search = lead_search[:10]
        
        for hit in lead_search.execute():
            results["leads"].append({
                'id': hit.meta.id,
                'lead_name': getattr(hit, 'lead_name', ''),
                'full_name': getattr(hit, 'full_name', ''),
                'phone_number': getattr(hit, 'phone_number', ''),
                'email': getattr(hit, 'email', ''),
                'status': getattr(hit, 'status', ''),
            })
        
        # Search Employees (admin only)
        if user.is_superuser or (hasattr(user, 'employee') and user.employee.role in ['ADMIN', 'BRANCH_MANAGER']):
            employee_search = Search(index='employees').query(
                "multi_match",
                query=query,
                fields=['username^2', 'designation', 'personal_phone'],
                fuzziness='AUTO'
            )[:10]
            
            for hit in employee_search.execute():
                results["employees"].append({
                    'id': hit.meta.id,
                    'username': getattr(hit, 'username', ''),
                    'designation': getattr(hit, 'designation', ''),
                    'personal_phone': getattr(hit, 'personal_phone', ''),
                })
        
        return results
    
    def _database_search(self, query, user):
        """Fallback search using Django ORM with permission filtering"""
        results = {
            "clients": [],
            "gst_details": [],
            "tasks": [],
            "invoices": [],
            "leads": [],
            "employees": []
        }
        
        # Import here to avoid circular imports
        from home.clients.client_access import get_accessible_clients
        
        # Get accessible clients for the user
        accessible_clients = get_accessible_clients(user)
        
        # Search clients
        clients = accessible_clients.filter(
            DjangoQ(client_name__icontains=query) |
            DjangoQ(pan_no__icontains=query) |
            DjangoQ(phone_number__icontains=query) |
            DjangoQ(email__icontains=query) |
            DjangoQ(file_number__icontains=query) |
            DjangoQ(city__icontains=query) |
            DjangoQ(state__icontains=query)
        )[:10]
        
        for client in clients:
            results["clients"].append({
                'id': client.id,
                'client_name': client.client_name,
                'pan_no': client.pan_no,
                'phone_number': client.phone_number,
                'email': client.email,
                'file_number': client.file_number or '',
                'city': client.city,
                'state': client.get_state_display(),
            })
        
        # Get accessible client IDs for filtering related models
        accessible_client_ids = accessible_clients.values_list('id', flat=True)
        
        # Search GST Details
        gst_details = GSTDetails.objects.select_related('client').filter(
            client_id__in=accessible_client_ids
        ).filter(
            DjangoQ(gst_number__icontains=query) |
            DjangoQ(state__icontains=query) |
            DjangoQ(client__client_name__icontains=query)
        )[:10]
        
        for gst in gst_details:
            results["gst_details"].append({
                'id': gst.id,
                'gst_number': gst.gst_number,
                'state': gst.get_state_display(),
                'client_name': gst.client.client_name,
            })
        
        # Search Tasks
        tasks = Task.objects.select_related('client').filter(
            client_id__in=accessible_client_ids
        ).filter(
            DjangoQ(task_title__icontains=query) |
            DjangoQ(description__icontains=query) |
            DjangoQ(service_type__icontains=query) |
            DjangoQ(status__icontains=query) |
            DjangoQ(client__client_name__icontains=query)
        )[:10]
        
        for task in tasks:
            results["tasks"].append({
                'id': task.id,
                'task_title': task.task_title,
                'description': task.description or '',
                'service_type': task.service_type,
                'status': task.status,
                'client_name': task.client.client_name,
            })
        
        # Search Invoices
        invoices = Invoice.objects.select_related('client').filter(
            client_id__in=accessible_client_ids
        ).filter(
            DjangoQ(subject__icontains=query) |
            DjangoQ(invoice_status__icontains=query) |
            DjangoQ(client__client_name__icontains=query)
        )[:10]
        
        for invoice in invoices:
            results["invoices"].append({
                'id': invoice.id,
                'subject': invoice.subject,
                'invoice_status': invoice.invoice_status,
                'client_name': invoice.client.client_name,
            })
        
        # Search Leads (user can see leads created by them or assigned to them)
        lead_filter = DjangoQ(created_by=user) | DjangoQ(assigned_to=user)
        
        leads = Lead.objects.filter(lead_filter).filter(
            DjangoQ(lead_name__icontains=query) |
            DjangoQ(full_name__icontains=query) |
            DjangoQ(phone_number__icontains=query) |
            DjangoQ(email__icontains=query) |
            DjangoQ(status__icontains=query)
        )[:10]
        
        for lead in leads:
            results["leads"].append({
                'id': lead.id,
                'lead_name': lead.lead_name,
                'full_name': lead.full_name,
                'phone_number': lead.phone_number,
                'email': lead.email or '',
                'status': lead.status,
            })
        
        # Search Employees (admin only)
        if user.is_superuser or (hasattr(user, 'employee') and user.employee.role in ['ADMIN', 'BRANCH_MANAGER']):
            employees = Employee.objects.select_related('user').filter(
                DjangoQ(user__username__icontains=query) |
                DjangoQ(designation__icontains=query) |
                DjangoQ(personal_phone__icontains=query)
            )[:10]
            
            for employee in employees:
                results["employees"].append({
                    'id': employee.id,
                    'username': employee.user.username,
                    'designation': employee.designation or '',
                    'personal_phone': employee.personal_phone or '',
                })
        
        return results
    
    def _empty_results(self):
        """Return empty results structure"""
        return {
            "clients": [],
            "gst_details": [],
            "tasks": [],
            "invoices": [],
            "leads": [],
            "employees": []
        }

# Global instance
search_service = GlobalSearchService()