from django.contrib.auth.models import User
from django.db import models

from django.utils import timezone
# -------------------------
# Client Base Table
# -------------------------
class Client(models.Model):
    CLIENT_TYPE_CHOICES = [
        ('Individual', 'Individual'),
        ('Entity', 'Entity'),
    ]

    BUSINESS_STRUCTURE_CHOICES = [
        ('Private Ltd', 'Private Ltd'),
        ('Public Ltd', 'Public Ltd'),
        ('LLP', 'LLP'),
        ('OPC', 'OPC'),
        ('Section 8', 'Section 8'),
    ]

    STATUS_CHOICES = [
        ('Prospect', 'Prospect'),
        ('Incorporation in progress', 'Incorporation in progress'),
        ('Incorporated', 'Incorporated'),
        ('Closed', 'Closed'),
        ('On-hold', 'On-hold'),
    ]

    client_name = models.CharField(max_length=255)
    primary_contact_name = models.CharField(max_length=255)
    pan_no = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    address_line1 = models.TextField()
    aadhar = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')
    date_of_engagement = models.DateField()
    assigned_ca = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clients_assigned'
    )
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES)
    business_structure = models.CharField(max_length=50, choices=BUSINESS_STRUCTURE_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Prospect')
    remarks = models.TextField(blank=True, null=True)
    din_no = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.client_name


# -------------------------
# Entity-Specific Details
# -------------------------
class CompanyDetails(models.Model):
    COMPANY_TYPE_CHOICES = [
        ('Private Limited', 'Private Limited'),
        ('Public Limited', 'Public Limited'),
        ('One Person Company', 'One Person Company'),
    ]

    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='company_details')
    company_type = models.CharField(max_length=50, choices=COMPANY_TYPE_CHOICES)
    proposed_company_name = models.CharField(max_length=255)
    cin = models.CharField(max_length=50, blank=True, null=True)
    authorised_share_capital = models.DecimalField(max_digits=15, decimal_places=2)
    paid_up_share_capital = models.DecimalField(max_digits=15, decimal_places=2)
    number_of_directors = models.PositiveIntegerField()
    number_of_shareholders = models.PositiveIntegerField()
    registered_office_address = models.TextField()
    date_of_incorporation = models.DateField(blank=True, null=True)
    udyam_registration = models.CharField(max_length=100, blank=True, null=True)
    directors = models.ManyToManyField(
        Client, related_name='companies_as_director', limit_choices_to={'din_no__isnull': False}, blank=True
    )
    moa_file = models.FileField(upload_to='company_docs/moa/', blank=True, null=True)
    aoa_file = models.FileField(upload_to='company_docs/aoa/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.proposed_company_name


class LLPDetails(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='llp_details')
    llp_name = models.CharField(max_length=255)
    llp_registration_no = models.CharField(max_length=50, blank=True, null=True)
    registered_office_address_llp = models.TextField()
    designated_partners = models.ManyToManyField(
        Client, related_name='llps_as_partner', limit_choices_to={'din_no__isnull': False}, blank=True
    )
    paid_up_capital_llp = models.DecimalField(max_digits=15, decimal_places=2)
    date_of_registration_llp = models.DateField(blank=True, null=True)
    llp_agreement_file = models.FileField(upload_to='llp_docs/agreements/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.llp_name


class OPCDetails(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='opc_details')
    opc_name = models.CharField(max_length=255)
    opc_cin = models.CharField(max_length=50, blank=True, null=True)
    registered_office_address_opc = models.TextField()
    sole_member_name = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, related_name='opcs_as_member')
    nominee_member_name = models.CharField(max_length=255)
    paid_up_share_capital_opc = models.DecimalField(max_digits=15, decimal_places=2)
    date_of_incorporation_opc = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.opc_name


class Section8CompanyDetails(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='section8_details')
    section8_company_name = models.CharField(max_length=255)
    registration_no_section8 = models.CharField(max_length=50, blank=True, null=True)
    registered_office_address_s8 = models.TextField()
    object_clause = models.TextField()
    whether_licence_obtained = models.BooleanField(default=False)
    date_of_registration_s8 = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.section8_company_name


class HUFDetails(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='huf_details')
    huf_name = models.CharField(max_length=255)
    pan_huf = models.CharField(max_length=20, unique=True)
    date_of_creation = models.DateField()
    karta_name = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, related_name='hufs_as_karta',
        limit_choices_to={'client_type': 'Individual'}
    )
    number_of_coparceners = models.PositiveIntegerField()
    number_of_members = models.PositiveIntegerField()
    residential_address = models.TextField()
    bank_account_details = models.JSONField(blank=True, null=True)
    deed_of_declaration_file = models.FileField(upload_to='huf_docs/deeds/', blank=True, null=True)
    business_activity = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.huf_name


# -------------------------
# Service Master
# -------------------------
class ServiceType(models.Model):
    FREQUENCY_CHOICES = [
        ('One-time', 'One-time'),
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Half-yearly', 'Half-yearly'),
        ('Yearly', 'Yearly'),
    ]

    CATEGORY_CHOICES = [
        ('Taxation', 'Taxation'),
        ('Audit', 'Audit'),
        ('Compliance', 'Compliance'),
        ('Consulting', 'Consulting'),
    ]

    service_name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    default_due_days = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    form_name = models.CharField(max_length=100, help_text="Form class name from forms.py (e.g., 'GSTDetailsForm')")
    model_name = models.CharField(max_length=100, help_text="Model class name for service details (e.g., 'GSTDetails')")
    allow_multiple = models.BooleanField(default=False, help_text="Can one client have multiple instances of this service?")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.service_name


# -------------------------
# Client Services
# -------------------------
class ClientService(models.Model):
    BILLING_CHOICES = [
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Yearly', 'Yearly'),
        ('Per Task', 'Per Task'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CHOICES)
    agreed_fee = models.DecimalField(max_digits=12, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client} - {self.service}"


# -------------------------
# Financial & Compliance
# -------------------------
class GSTDetails(models.Model):
    REGISTRATION_TYPE_CHOICES = [
        ('Regular', 'Regular'),
        ('Composition', 'Composition'),
        ('Casual', 'Casual'),
        ('Non-Resident', 'Non-Resident'),
    ]

    FILING_FREQUENCY_CHOICES = [
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Annual', 'Annual'),
    ]

    gst_id = models.AutoField(primary_key=True)
    client_service = models.ForeignKey(ClientService, on_delete=models.CASCADE, related_name='gst_details')
    gst_number = models.CharField(max_length=15, unique=True)
    date_of_registration = models.DateField(blank=True, null=True)
    type_of_registration = models.CharField(max_length=20, choices=REGISTRATION_TYPE_CHOICES)
    gst_username = models.CharField(max_length=100)
    gst_password = models.CharField(max_length=255)
    principal_place_of_business = models.TextField()
    filing_frequency = models.CharField(max_length=20, choices=FILING_FREQUENCY_CHOICES)
    state_code = models.CharField(max_length=5)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.gst_number


class ITRDetails(models.Model):
    ITR_TYPE_CHOICES = [
        ('ITR-1', 'ITR-1'),
        ('ITR-2', 'ITR-2'),
        ('ITR-3', 'ITR-3'),
        ('ITR-4', 'ITR-4'),
        ('ITR-5', 'ITR-5'),
        ('ITR-6', 'ITR-6'),
        ('ITR-7', 'ITR-7'),
    ]

    FILING_MODE_CHOICES = [
        ('Self', 'Self'),
        ('Through CA', 'Through CA'),
    ]

    itr_id = models.AutoField(primary_key=True)
    client_service = models.ForeignKey(ClientService, on_delete=models.CASCADE, related_name='itr_details')
    pan_number = models.CharField(max_length=20)
    aadhaar_number = models.CharField(max_length=20, blank=True, null=True)
    itr_type = models.CharField(max_length=10, choices=ITR_TYPE_CHOICES)
    assessment_year = models.CharField(max_length=9)  # e.g., "2024-25"
    income_source = models.CharField(max_length=100)
    last_itr_ack_no = models.CharField(max_length=50, blank=True, null=True)
    filing_mode = models.CharField(max_length=20, choices=FILING_MODE_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pan_number} - {self.assessment_year}"


class AuditDetails(models.Model):
    AUDIT_TYPE_CHOICES = [
        ('Statutory', 'Statutory'),
        ('Tax', 'Tax'),
        ('Internal', 'Internal'),
        ('Stock', 'Stock'),
        ('Other', 'Other'),
    ]

    audit_id = models.AutoField(primary_key=True)
    client_service = models.ForeignKey(ClientService, on_delete=models.CASCADE, related_name='audit_details')
    audit_type = models.CharField(max_length=20, choices=AUDIT_TYPE_CHOICES)
    financial_year = models.CharField(max_length=9)  # e.g., "2023-24"
    auditor_name = models.CharField(max_length=255)
    audit_start_date = models.DateField(blank=True, null=True)
    audit_end_date = models.DateField(blank=True, null=True)
    report_upload = models.FileField(upload_to='audit_docs/reports/', blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.audit_type} Audit - {self.financial_year}"


# -------------------------
# Tasks & Activities
# -------------------------
class Task(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Submitted', 'Submitted'),
        ('Completed', 'Completed'),
        ('Delayed', 'Delayed'),
        ('Cancelled', 'Cancelled'),
    ]

    RECURRENCE_CHOICES = [
        ('None', 'None'),
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Yearly', 'Yearly'),
    ]

    client_service = models.ForeignKey(ClientService, on_delete=models.CASCADE, related_name='tasks')
    task_title = models.CharField(max_length=255)
    period_from = models.DateField(blank=True, null=True)
    period_to = models.DateField(blank=True, null=True)
    due_date = models.DateField()
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    task_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    completion_date = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    recurrence = models.CharField(max_length=20, choices=RECURRENCE_CHOICES, default='None')
    parent_task = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    document_link = models.FileField(upload_to='task_documents/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.task_title


class TaskActivityLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.task_title} - {self.action}"


# -------------------------
# Legal Cases
# -------------------------
class IncomeTaxCaseDetails(models.Model):
    CASE_TYPE_CHOICES = [
        ('Scrutiny', 'Scrutiny'),
        ('Reassessment', 'Reassessment'),
        ('Appeal', 'Appeal'),
        ('Rectification', 'Rectification'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Submitted', 'Submitted'),
        ('Closed', 'Closed'),
    ]

    case_id = models.AutoField(primary_key=True)
    client_service = models.ForeignKey(ClientService, on_delete=models.CASCADE, related_name='incometax_case_details')
    case_type = models.CharField(max_length=20, choices=CASE_TYPE_CHOICES)
    notice_number = models.CharField(max_length=100, blank=True, null=True)
    notice_date = models.DateField(blank=True, null=True)
    ao_name = models.CharField(max_length=255)
    ward_circle = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    last_hearing_date = models.DateField(blank=True, null=True)
    next_hearing_date = models.DateField(blank=True, null=True)
    documents_link = models.FileField(upload_to='income_tax_cases/docs/', blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.case_type} - {self.status}"


class GSTCaseDetails(models.Model):
    CASE_TYPE_CHOICES = [
        ('Show Cause Notice', 'Show Cause Notice'),
        ('Demand', 'Demand'),
        ('Appeal', 'Appeal'),
        ('Refund', 'Refund'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Submitted', 'Submitted'),
        ('Closed', 'Closed'),
    ]

    gst_case_id = models.AutoField(primary_key=True)
    client_service = models.ForeignKey(ClientService, on_delete=models.CASCADE, related_name='gst_case_details')
    case_type = models.CharField(max_length=50, choices=CASE_TYPE_CHOICES)
    gstin = models.CharField(max_length=15)
    case_number = models.CharField(max_length=100)
    date_of_notice = models.DateField()
    officer_name = models.CharField(max_length=100)
    jurisdiction = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.case_type} - {self.case_number}"


# -------------------------
# Client User Mapping
# -------------------------
class ClientUserEntitle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_mappings')
    clients = models.ManyToManyField(Client, related_name='user_mappings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        client_names = ", ".join([client.client_name for client in self.clients.all()[:3]])
        if self.clients.count() > 3:
            client_names += f" and {self.clients.count() - 3} more"
        return f"{self.user.username} - {client_names}"

    class Meta:
        unique_together = ('user',)


class DocumentMaster(models.Model):
    category = models.CharField(max_length=100)
    document_name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.category} - {self.document_name}"


class DocumentRequest(models.Model):
    # Represents a document collection cycle for one client (or optionally all clients)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='document_requests')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField()
    created_by = models.ForeignKey(User, related_name='created_requests', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    for_all_clients = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.client.client_name}) - due {self.due_date}"

    @property
    def is_overdue(self):
        return timezone.localdate() > self.due_date


class RequestedDocument(models.Model):
    document_request = models.ForeignKey(DocumentRequest, related_name='required_documents', on_delete=models.CASCADE)
    document_master = models.ForeignKey(DocumentMaster, on_delete=models.PROTECT)

    class Meta:
        unique_together = ('document_request', 'document_master')

    def __str__(self):
        return f"{self.document_master.document_name} for request {self.document_request.id}"


class ClientDocumentUpload(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Uploaded', 'Uploaded'),
        ('Overdue', 'Overdue'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='document_uploads')
    requested_document = models.ForeignKey(RequestedDocument, related_name='uploads', on_delete=models.CASCADE)
    uploaded_file = models.FileField(upload_to='client_documents/%Y/%m/%d/')
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    remarks = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who uploaded the document")

    def save(self, *args, **kwargs):
        if self.uploaded_file:
            self.status = 'Uploaded'
        try:
            if self.requested_document.document_request.is_overdue and self.status != 'Uploaded':
                self.status = 'Overdue'
        except Exception:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Upload by {self.client.client_name} for {self.requested_document}"
