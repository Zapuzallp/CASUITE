from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from home.models import (
    Client, ClientBusinessProfile, GSTDetails, 
    Task, Invoice, Employee, Lead
)


@registry.register_document
class ClientDocument(Document):
    """Elasticsearch document for Client model"""
    
    # Related fields
    assigned_ca_name = fields.TextField(attr='assigned_ca.get_full_name')
    office_location_name = fields.TextField(attr='office_location.office_name')
    
    class Index:
        name = 'clients'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Client
        fields = [
            'id',
            'file_number',
            'client_name',
            'primary_contact_name',
            'pan_no',
            'aadhar',
            'din_no',
            'tan_no',
            'email',
            'phone_number',
            'father_name',
            'address_line1',
            'postal_code',
            'city',
            'state',
            'client_type',
            'business_structure',
            'status',
            'remarks',
        ]


@registry.register_document
class ClientBusinessProfileDocument(Document):
    """Elasticsearch document for ClientBusinessProfile model"""
    
    client_name = fields.TextField(attr='client.client_name')
    client_id = fields.IntegerField(attr='client.id')
    
    class Index:
        name = 'client_business_profiles'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = ClientBusinessProfile
        fields = [
            'id',
            'registration_number',
            'date_of_incorporation',
            'registered_office_address',
            'udyam_registration',
            'object_clause',
        ]


@registry.register_document
class GSTDetailsDocument(Document):
    """Elasticsearch document for GSTDetails model"""
    
    client_name = fields.TextField(attr='client.client_name')
    client_id = fields.IntegerField(attr='client.id')
    client_pan = fields.TextField(attr='client.pan_no')
    
    class Index:
        name = 'gst_details'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = GSTDetails
        fields = [
            'id',
            'gst_number',
            'registered_address',
            'state',
            'gst_scheme_type',
            'status',
        ]


@registry.register_document
class TaskDocument(Document):
    """Elasticsearch document for Task model"""
    
    client_name = fields.TextField(attr='client.client_name')
    client_id = fields.IntegerField(attr='client.id')
    created_by_name = fields.TextField(attr='created_by.get_full_name')
    
    # Get assignee names
    assignee_names = fields.TextField()
    
    class Index:
        name = 'tasks'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Task
        fields = [
            'id',
            'service_type',
            'task_title',
            'description',
            'due_date',
            'priority',
            'status',
            'recurrence_period',
            'fee_status',
            'consultancy_type',
        ]
    
    def prepare_assignee_names(self, instance):
        """Prepare assignee names for indexing"""
        return ' '.join([user.get_full_name() or user.username for user in instance.assignees.all()])


@registry.register_document
class InvoiceDocument(Document):
    """Elasticsearch document for Invoice model"""
    
    client_name = fields.TextField(attr='client.client_name')
    client_id = fields.IntegerField(attr='client.id')
    invoice_number = fields.TextField()
    
    class Index:
        name = 'invoices'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Invoice
        fields = [
            'id',
            'subject',
            'invoice_status',
            'due_date',
            'invoice_date',
        ]
    
    def prepare_invoice_number(self, instance):
        """Prepare invoice number for indexing"""
        return f"INV-{instance.id}"


@registry.register_document
class EmployeeDocument(Document):
    """Elasticsearch document for Employee model"""
    
    username = fields.TextField(attr='user.username')
    first_name = fields.TextField(attr='user.first_name')
    last_name = fields.TextField(attr='user.last_name')
    email = fields.TextField(attr='user.email')
    full_name = fields.TextField()
    office_location_name = fields.TextField(attr='office_location.office_name')
    supervisor_name = fields.TextField(attr='supervisor.get_full_name')
    
    class Index:
        name = 'employees'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Employee
        fields = [
            'id',
            'designation',
            'personal_phone',
            'work_phone',
            'personal_email',
            'address',
            'role',
        ]
    
    def prepare_full_name(self, instance):
        """Prepare full name for indexing"""
        return instance.user.get_full_name() or instance.user.username


@registry.register_document
class LeadDocument(Document):
    """Elasticsearch document for Lead model"""
    
    created_by_name = fields.TextField(attr='created_by.get_full_name')
    assigned_to_names = fields.TextField()
    
    class Index:
        name = 'leads'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Lead
        fields = [
            'id',
            'lead_name',
            'full_name',
            'email',
            'phone_number',
            'requirements',
            'lead_value',
            'status',
            'remarks',
        ]
    
    def prepare_assigned_to_names(self, instance):
        """Prepare assigned user names for indexing"""
        return ' '.join([user.get_full_name() or user.username for user in instance.assigned_to.all()])