from django_elasticsearch_dsl import Document, Index, fields
from django_elasticsearch_dsl.registries import registry
from .models import Client, GSTDetails, Task, Invoice, Lead, Employee

# Define indexes
client_index = Index('clients')
gst_details_index = Index('gst_details')
task_index = Index('tasks')
invoice_index = Index('invoices')
lead_index = Index('leads')
employee_index = Index('employees')

# Configure index settings
client_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@registry.register_document
class ClientDocument(Document):
    """Elasticsearch document for Client model with permission fields"""
    
    # Permission fields for filtering
    client_id = fields.IntegerField()
    assigned_ca_id = fields.IntegerField()
    created_by_id = fields.IntegerField()
    office_location_id = fields.IntegerField()
    
    class Index:
        name = 'clients'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Client
        fields = [
            'client_name',
            'pan_no',
            'phone_number',
            'email',
            'file_number',
            'city',
            'state',
        ]

    def prepare_client_id(self, instance):
        return instance.id

    def prepare_assigned_ca_id(self, instance):
        return instance.assigned_ca_id if instance.assigned_ca_id else 0

    def prepare_created_by_id(self, instance):
        return instance.created_by_id if instance.created_by_id else 0

    def prepare_office_location_id(self, instance):
        return instance.office_location_id if instance.office_location_id else 0

@registry.register_document
class GSTDetailsDocument(Document):
    """Elasticsearch document for GSTDetails model with client permission inheritance"""
    
    client_name = fields.TextField(attr='client.client_name')
    
    # Permission fields inherited from client
    client_id = fields.IntegerField()
    assigned_ca_id = fields.IntegerField()
    created_by_id = fields.IntegerField()
    office_location_id = fields.IntegerField()
    
    class Index:
        name = 'gst_details'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = GSTDetails
        fields = [
            'gst_number',
            'state',
        ]
        related_models = [Client]

    def get_queryset(self):
        return super().get_queryset().select_related('client')

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Client):
            return related_instance.gst_details.all()

    def prepare_client_id(self, instance):
        return instance.client.id

    def prepare_assigned_ca_id(self, instance):
        return instance.client.assigned_ca_id if instance.client.assigned_ca_id else 0

    def prepare_created_by_id(self, instance):
        return instance.client.created_by_id if instance.client.created_by_id else 0

    def prepare_office_location_id(self, instance):
        return instance.client.office_location_id if instance.client.office_location_id else 0

@registry.register_document
class TaskDocument(Document):
    """Elasticsearch document for Task model with client permission inheritance"""
    
    client_name = fields.TextField(attr='client.client_name')
    
    # Permission fields inherited from client
    client_id = fields.IntegerField()
    assigned_ca_id = fields.IntegerField()
    created_by_id = fields.IntegerField()
    office_location_id = fields.IntegerField()
    
    class Index:
        name = 'tasks'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Task
        fields = [
            'task_title',
            'description',
            'service_type',
            'status',
        ]
        related_models = [Client]

    def get_queryset(self):
        return super().get_queryset().select_related('client')

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Client):
            return related_instance.tasks.all()

    def prepare_client_id(self, instance):
        return instance.client.id

    def prepare_assigned_ca_id(self, instance):
        return instance.client.assigned_ca_id if instance.client.assigned_ca_id else 0

    def prepare_created_by_id(self, instance):
        return instance.client.created_by_id if instance.client.created_by_id else 0

    def prepare_office_location_id(self, instance):
        return instance.client.office_location_id if instance.client.office_location_id else 0

@registry.register_document
class InvoiceDocument(Document):
    """Elasticsearch document for Invoice model with client permission inheritance"""
    
    client_name = fields.TextField(attr='client.client_name')
    
    # Permission fields inherited from client
    client_id = fields.IntegerField()
    assigned_ca_id = fields.IntegerField()
    created_by_id = fields.IntegerField()
    office_location_id = fields.IntegerField()
    
    class Index:
        name = 'invoices'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Invoice
        fields = [
            'subject',
            'invoice_status',
        ]
        related_models = [Client]

    def get_queryset(self):
        return super().get_queryset().select_related('client')

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Client):
            return related_instance.invoices.all()

    def prepare_client_id(self, instance):
        return instance.client.id

    def prepare_assigned_ca_id(self, instance):
        return instance.client.assigned_ca_id if instance.client.assigned_ca_id else 0

    def prepare_created_by_id(self, instance):
        return instance.client.created_by_id if instance.client.created_by_id else 0

    def prepare_office_location_id(self, instance):
        return instance.client.office_location_id if instance.client.office_location_id else 0

@registry.register_document
class LeadDocument(Document):
    """Elasticsearch document for Lead model with permission fields"""
    
    # Permission fields for leads
    created_by_id = fields.IntegerField()
    assigned_to_ids = fields.IntegerField(multi=True)  # For many-to-many assigned_to field
    
    class Index:
        name = 'leads'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Lead
        fields = [
            'lead_name',
            'full_name',
            'phone_number',
            'email',
            'status',
        ]

    def prepare_created_by_id(self, instance):
        return instance.created_by_id if instance.created_by_id else 0

    def prepare_assigned_to_ids(self, instance):
        return list(instance.assigned_to.values_list('id', flat=True))

@registry.register_document
class EmployeeDocument(Document):
    """Elasticsearch document for Employee model with permission fields"""
    
    username = fields.TextField(attr='user.username')
    
    # Permission fields for employees (admin-only access)
    office_location_id = fields.IntegerField()
    
    class Index:
        name = 'employees'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Employee
        fields = [
            'designation',
            'personal_phone',
        ]
        related_models = ['auth.User']

    def get_queryset(self):
        return super().get_queryset().select_related('user')

    def get_instances_from_related(self, related_instance):
        from django.contrib.auth.models import User
        if isinstance(related_instance, User):
            try:
                return [related_instance.employee]
            except Employee.DoesNotExist:
                return []

    def prepare_office_location_id(self, instance):
        return instance.office_location_id if instance.office_location_id else 0