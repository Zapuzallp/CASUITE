from django.contrib.auth.models import User
from django.contrib.auth.models import User
# -------------------------
# Client Base Table
# -------------------------
from django.db import models
from django.utils import timezone


# -------------------------
# 1. Base Client Model
# -------------------------
class Client(models.Model):
    CLIENT_TYPE_CHOICES = [
        ('Individual', 'Individual'),
        ('Entity', 'Entity'),
    ]

    BUSINESS_STRUCTURE_CHOICES = [
        ('Proprietorship', 'Proprietorship'),
        ('Private Ltd', 'Private Limited'),
        ('Public Ltd', 'Public Limited'),
        ('LLP', 'Limited Liability Partnership'),
        ('OPC', 'One Person Company'),
        ('Section 8', 'Section 8 Company'),
        ('HUF', 'Hindu Undivided Family'),
        ('Partnership', 'Partnership Firm'),
    ]

    STATUS_CHOICES = [
        ('Prospect', 'Prospect'),
        ('Incorporation in progress', 'Incorporation in progress'),
        ('Incorporated', 'Incorporated'),
        ('Closed', 'Closed'),
        ('On-hold', 'On-hold'),
    ]

    # --- Basic Identity ---
    client_name = models.CharField(max_length=255, help_text="Name of Individual or Entity")
    primary_contact_name = models.CharField(max_length=255, help_text="Name of the person to contact")

    # --- Identifiers ---
    pan_no = models.CharField(max_length=20, unique=True, verbose_name="PAN Number")
    aadhar = models.CharField(max_length=20, blank=True, null=True, verbose_name="Aadhar Number")
    din_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="DIN",
                              help_text="Director Identification Number (if Individual)")
    tan_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="TAN")

    # --- Contact Info ---
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    Father_Name = models.CharField(max_length=200, blank=True, null=True)

    # --- Address ---
    address_line1 = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')

    # --- Management ---
    date_of_engagement = models.DateField(default=models.functions.Now)
    assigned_ca = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='clients_assigned')

    # --- Classification ---
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES)
    business_structure = models.CharField(max_length=50, choices=BUSINESS_STRUCTURE_CHOICES, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Prospect')

    # --- Meta ---
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='clients_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.client_name


class GSTDetails(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='gst_details')
    gst_number = models.CharField(max_length=15)
    registered_address = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.gst_number} - {self.state}"
# -------------------------
# 2. Universal Business Profile
# -------------------------
class ClientBusinessProfile(models.Model):
    """
    Stores entity-specific details.
    Fields are nullable in DB but enforced as 'Required' in Forms/UI based on business_structure.
    """
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='business_profile')

    # --- Registration Details ---
    # Maps to: CIN (Companies), LLPIN (LLP), Registration No (Section 8/Trust)
    registration_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="CIN / LLPIN / Reg No")
    date_of_incorporation = models.DateField(blank=True, null=True, verbose_name="Date of Incorp/Formation")
    registered_office_address = models.TextField(blank=True, null=True)
    udyam_registration = models.CharField(max_length=100, blank=True, null=True, verbose_name="MSME/Udyam Reg")

    # --- Capital Info (Companies / LLP / OPC) ---
    authorised_capital = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    paid_up_capital = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True,
                                          verbose_name="Paid-up Capital / Contribution")

    # --- Structure Counts ---
    number_of_directors = models.PositiveIntegerField(blank=True, null=True)
    number_of_shareholders = models.PositiveIntegerField(blank=True, null=True)
    number_of_members = models.PositiveIntegerField(blank=True, null=True)  # For HUF, Section 8, OPC

    # --- Key Personnel Relationships ---
    # HUF Karta
    karta = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='huf_as_karta', limit_choices_to={'client_type': 'Individual'}
    )
    # HUF Coparceners
    number_of_coparceners = models.PositiveIntegerField(blank=True, null=True)

    # OPC Nominee
    opc_nominee_name = models.CharField(max_length=255, blank=True, null=True)

    # --- Many-to-Many Relationships ---
    # Directors / Designated Partners / Members
    key_persons = models.ManyToManyField(
        Client, related_name='associated_entities', blank=True,
        help_text="Select Directors, Partners, or Members already in the database."
    )

    # --- Specific Clauses ---
    object_clause = models.TextField(blank=True, null=True, help_text="Main Objects / Business Activity")
    is_section8_license_obtained = models.BooleanField(default=False, verbose_name="Section 8 License Obtained?")

    # --- Documents (Generic Slots) ---
    # Document 1: MOA / LLP Agreement / HUF Deed / Partnership Deed
    constitution_document_1 = models.FileField(upload_to='entity_docs/const_1/', blank=True, null=True)
    # Document 2: AOA / By-Laws
    constitution_document_2 = models.FileField(upload_to='entity_docs/const_2/', blank=True, null=True)

    def __str__(self):
        return f"Profile: {self.client.client_name}"

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


class Task(models.Model):
    # Static Service Choices matching Config Keys
    SERVICE_TYPE_CHOICES = [
        ('GST Return', 'GST Return Filing'),
        ('ITR Filing', 'Income Tax Return (ITR)'),
        ('Audit', 'Audit Services'),
        ('ROC Compliance', 'ROC / MCA Compliance'),
        ('TDS Return', 'TDS Return Filing'),
        ('Consultancy', 'General Consultancy'),
    ]

    PRIORITY_CHOICES = [('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')]

    # Generic Status Choices (Config dictates actual workflow)
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Review', 'Review'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled')
    ]

    RECURRENCE_CHOICES = [
        ('None', 'One-time'),
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Yearly', 'Yearly'),
    ]

    # --- Core Links ---
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='tasks')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tasks')

    # CHANGED: Multi-User Assignment
    assignees = models.ManyToManyField(User, related_name='assigned_tasks', blank=True)

    # --- Task Details ---
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES)
    task_title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # --- Dates & Status ---
    due_date = models.DateField()
    completed_date = models.DateField(blank=True, null=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')

    # Current Overall Stage (Controlled by Workflow)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    # --- Recurrence & Financials ---
    recurrence_period = models.CharField(max_length=20, choices=RECURRENCE_CHOICES, default='None')

    agreed_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    fee_status = models.CharField(max_length=20, default='Unbilled', choices=[
        ('Unbilled', 'Unbilled'), ('Billed', 'Billed'), ('Paid', 'Paid')
    ])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_title} ({self.client.client_name})"

    # Helper to log status changes
    def log_status_change(self, old_status, new_status, changed_by, remarks=None):
        if old_status != new_status:
            TaskStatusLog.objects.create(
                task=self,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
                remarks=remarks
            )


class TaskAssignmentStatus(models.Model):
    """
    Tracks individual completion for the CURRENT status workflow step.
    This allows 'Collaboration': 2 people assigned, both must finish before task moves.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignment_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Which status workflow step are they working on?
    status_context = models.CharField(max_length=50)

    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    class Meta:
        unique_together = ('task', 'user', 'status_context')
        ordering = ['order']
        unique_together = ('task', 'user', 'status_context')

    def __str__(self):
        return f"{self.user.username} - {self.status_context} ({'Done' if self.is_completed else 'Pending'})"


class TaskStatusLog(models.Model):
    """
    Tracks the history of status changes to calculate aging and who moved it.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='status_logs')
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.task_title}: {self.old_status} -> {self.new_status}"


class TaskExtendedAttributes(models.Model):
    """
    SUPERSET TABLE: Contains fields for ALL possible service types.
    """
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='extended_attributes')

    # --- Financials ---
    period_month = models.CharField(max_length=20, blank=True, null=True)
    period_year = models.CharField(max_length=10, blank=True, null=True)
    financial_year = models.CharField(max_length=10, blank=True, null=True)
    assessment_year = models.CharField(max_length=10, blank=True, null=True)
    total_turnover = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    gross_total_income = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tax_payable = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    audit_fee = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # --- Identifiers ---
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    gstin_number = models.ForeignKey(GSTDetails, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    ack_number = models.CharField(max_length=50, blank=True, null=True)
    arn_number = models.CharField(max_length=50, blank=True, null=True)
    udin_number = models.CharField(max_length=50, blank=True, null=True)
    srn_number = models.CharField(max_length=50, blank=True, null=True)
    din_numbers = models.TextField(blank=True, null=True)

    # --- Dates ---
    filing_date = models.DateField(blank=True, null=True)
    date_of_signing = models.DateField(blank=True, null=True)
    meeting_date = models.DateField(blank=True, null=True)

    # --- Files ---
    json_file = models.FileField(upload_to='tasks/json/', blank=True, null=True)
    computation_file = models.FileField(upload_to='tasks/computations/', blank=True, null=True)
    ack_file = models.FileField(upload_to='tasks/ack/', blank=True, null=True)
    audit_report_file = models.FileField(upload_to='tasks/audit_reports/', blank=True, null=True)

    GST_RETURN_TYPES = [
        ('GSTR-1', 'GSTR-1'),
        ('GSTR-3B', 'GSTR-3B'),
        ('GSTR-9', 'GSTR-9'),
        ('CMP-08', 'CMP-08'),
        ('NONE', 'None'),  # optional
    ]

    gst_return_type = models.CharField(
        max_length=20,
        choices=GST_RETURN_TYPES,
        blank=True,
        null=True,
        help_text="Select GST return type"
    )

    # Granular Tax Breakup
    taxable_value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    igst_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    cgst_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    sgst_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    cess_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # Input Tax Credit (ITC)
    itc_available = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    itc_claimed = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # Penalties & Payments
    late_fee_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    interest_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    challan_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    challan_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Extended Data for Task {self.task.id}"


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class TaskDocument(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='task_documents/%Y/%m/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)



#------------------------------------
# Employee Details
#------------------------------------

class Employee(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='employee')
    designation = models.CharField(max_length=255,blank=True,null=True)
    personal_phone = models.CharField(max_length=20,blank=True,null=True)
    work_phone = models.CharField(max_length=20,blank=True,null=True)
    personal_email = models.EmailField(blank=True,null=True)
    address = models.TextField(blank=True,null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/',blank=True,null=True  )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

