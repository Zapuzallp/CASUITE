from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db import models
# -------------------------
# Client Base Table
# -------------------------
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings


# Create your models here.

# -----------------------------------------
# 1. Shift Table
# -----------------------------------------


class Shift(models.Model):
    DAY_CHOICES = (
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    )

    shift_name = models.CharField(max_length=100)
    shift_start_time = models.TimeField()
    shift_end_time = models.TimeField()
    # Maximum allowed duration in hours (e.g., 8.5 for 8 hours 30 mins)
    maximum_allowed_duration = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="Maximum permitted duration in hours (example: 8.5)"
    )
    # Day off stored as a comma-separated string (e.g., 'Sat,Sun')
    days_off = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=DAY_CHOICES
    )

    def __str__(self):
        return self.shift_name


# -----------------------------------------
# 2. Employee Shift Table
# -----------------------------------------


class EmployeeShift(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='employee_shifts')
    shift = models.ForeignKey(
        Shift, on_delete=models.CASCADE, related_name='assigned_employees')
    # Optional: Track this assignment validity
    valid_from = models.DateField(auto_now_add=True)
    valid_to = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_username()} assigned to {self.shift.shift_name}"


STATE_CHOICES = (
    ('01', 'West Bengal'),
    ('02', 'Himachal Pradesh'),
    ('03', 'Punjab'),
    ('04', 'Chandigarh'),
    ('05', 'Uttarakhand'),
    ('06', 'Haryana'),
    ('07', 'Delhi'),
    ('08', 'Rajasthan'),
    ('09', 'Uttar Pradesh'),
    ('10', 'Bihar'),
    ('11', 'Sikkim'),
    ('12', 'Arunachal Pradesh'),
    ('13', 'Nagaland'),
    ('14', 'Manipur'),
    ('15', 'Mizoram'),
    ('16', 'Tripura'),
    ('17', 'Meghalaya'),
    ('18', 'Assam'),
    ('19', 'Jammu and Kashmir'),
    ('20', 'Jharkhand'),
    ('21', 'Odisha'),
    ('22', 'Chhattisgarh'),
    ('23', 'Madhya Pradesh'),
    ('24', 'Gujarat'),
    # Note: 26 is the merged code for Daman, Diu, Dadra & Nagar Haveli
    ('26', 'Dadra and Nagar Haveli and Daman and Diu'),
    ('27', 'Maharashtra'),
    ('29', 'Karnataka'),
    ('30', 'Goa'),
    ('31', 'Lakshadweep'),
    ('32', 'Kerala'),
    ('33', 'Tamil Nadu'),
    ('34', 'Puducherry'),
    ('35', 'Andaman and Nicobar Islands'),
    ('36', 'Telangana'),
    ('37', 'Andhra Pradesh'),
    ('38', 'Ladakh'),
    ('97', 'Other Territory'),
)


# -----------------------------------------
# 3. Office Details Table
# -----------------------------------------


class OfficeDetails(models.Model):
    office_name = models.CharField(max_length=100)
    state = models.CharField(
        max_length=2,
        choices=STATE_CHOICES,  # <--- Here we used the list of states.
        blank=True,  # allow blank in form
        null=True,
        default="West Bengal",
        help_text="Choose you office state."
    )
    office_full_address = models.TextField()
    contact_person_name = models.CharField(max_length=100)
    office_contact_no = models.CharField(max_length=20)
    # Store Lat/Long as Decimal fields for accuracy
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Office details"

        verbose_name = "Office detail"

    def __str__(self):
        return self.office_name


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

    # ----- File Number --------
    file_number = models.CharField(max_length=10, unique=True, blank=True, null=True)

    # --- Basic Identity ---
    client_name = models.CharField(max_length=255, help_text="Name of Individual or Entity")
    primary_contact_name = models.CharField(max_length=255, help_text="Name of the person to contact")

    # --- Identifiers ---
    pan_no = models.CharField(max_length=20, unique=True, verbose_name="PAN Number")
    aadhar = models.CharField(max_length=20, blank=True, null=True, verbose_name="Aadhar Number")
    aadhar_linked_mobile = models.BooleanField(default=False, verbose_name="Aadhar Linked With Mobile ?")
    din_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="DIN",
                              help_text="Director Identification Number (if Individual)")
    tan_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="TAN")

    # --- Contact Info ---
    email = models.EmailField()
    phone_number = models.CharField(max_length=255)
    father_name = models.CharField(max_length=100, blank=True, null=True)

    # --- Address ---
    address_line1 = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, choices=STATE_CHOICES)

    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')

    office_location = models.ForeignKey(
        OfficeDetails,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients'
    )

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


GST_SCHEME_CHOICES = [
    ('Regular', 'Regular Scheme'),
    ('Composition', 'Composition Scheme'),
    ('QRMP', 'QRMP Scheme'),
]

GST_STATUS_CHOICES = [
    ('Active', 'Active'),
    ('Closed', 'Closed'),
]


class GSTDetails(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='gst_details')

    gst_number = models.CharField(max_length=15)

    registered_address = models.TextField(blank=True, null=True)

    #  State dropdown
    state = models.CharField(
        max_length=2,
        choices=STATE_CHOICES,
        blank=True,
        null=True
    )

    #  NEW FIELD 1: GST Scheme Type
    gst_scheme_type = models.CharField(
        max_length=20,
        choices=GST_SCHEME_CHOICES
    )

    #  NEW FIELD 2: Created By (logged-in user)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gst_created'
    )

    #  NEW FIELD 3: Status
    status = models.CharField(
        max_length=10,
        choices=GST_STATUS_CHOICES,
        default='Active'
    )

    def __str__(self):
        return f"{self.gst_number} - {self.get_state_display()}"


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
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    help_text="User who uploaded the document")

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
    due_date = models.DateField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')

    # Current Overall Stage (Controlled by Workflow)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    # --- Recurrence & Financials ---
    is_recurring = models.BooleanField(default=False)
    recurrence_period = models.CharField(max_length=20, choices=RECURRENCE_CHOICES, default='None')

    agreed_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    fee_status = models.CharField(max_length=20, default='Unbilled', choices=[
        ('Unbilled', 'Unbilled'), ('Billed', 'Billed'), ('Paid', 'Paid')
    ])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # 🔑 This prevents duplicate auto-creation
    last_auto_created_at = models.DateTimeField(null=True, blank=True)

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

    # Set `is_recurring` only when the task is first created.
    # Derived from `recurrence_period` to avoid auto-created
    # or copied tasks being incorrectly marked as recurring.
    def save(self, *args, **kwargs):
        if self.pk and not self.description:
            old = Task.objects.get(pk=self.pk)
            self.description = old.description
        self.is_recurring = self.recurrence_period != 'None'
        super().save(*args, **kwargs)


class TaskRecurrence(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="task_recurrence")
    recurrence_period = models.CharField(max_length=20)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_auto_created_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.recurrence_period == "None":
            raise ValidationError(
                {"recurrence_period": "TaskRecurrence cannot be 'None'"}
            )

    def __str__(self):
        return self.task.task_title


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


from datetime import timedelta


class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()

    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)

    duration = models.DurationField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("half_day", "Half Day Present"),
            ("full_day", "Full Day Present")
        ],
        default="approved"
    )

    remark = models.TextField(blank=True, null=True)

    location_name = models.CharField(max_length=255, null=True, blank=True)
    clock_in_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    clock_in_long = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    clock_out_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    clock_out_long = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    class Meta:
        unique_together = ('user', 'date')

    def save(self, *args, **kwargs):

        # Calculate duration
        if self.clock_in and self.clock_out:
            if self.clock_out < self.clock_in:
                self.clock_out += timedelta(days=1)

            self.duration = self.clock_out - self.clock_in

            # Only auto-set status if admin logic didn’t already set it
            if not hasattr(self, '_skip_auto_status') and (not self.status or self.status == "approved"):
                self.status = "approved"

        elif self.clock_in and not self.clock_out:
            if not hasattr(self, '_skip_auto_status') and not self.status:
                self.status = "pending"
            self.duration = None

        else:
            if not hasattr(self, '_skip_auto_status') and not self.status:
                self.status = "absent"
            self.duration = None

        super().save(*args, **kwargs)

    def formatted_duration(self):
        if not self.duration:
            return "-"

        total_seconds = int(self.duration.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m {seconds}s"

    def get_work_duration(self):
        """Get formatted work duration for mobile display"""
        if self.clock_in and not self.clock_out:
            # Calculate current duration
            current_time = timezone.now()
            duration = current_time - self.clock_in
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}:00 Hrs"
        elif self.duration:
            return self.formatted_duration()
        return "00:00:00 Hrs"

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class Notification(models.Model):
    TAG_CHOICES = (
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    tag = models.CharField(
        max_length=20,
        choices=TAG_CHOICES,
        default='info'
    )
    target_url = models.CharField(
        max_length=255,
        blank=True
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} → {self.user.username}"


ROLES_CHOICE = [
    ('BRANCH_MANAGER', 'Branch Manager'),
    ('ADMIN', 'Administrator'),
    ('STAFF', 'Staff')
]


# Employee and Leave table
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee")
    designation = models.CharField(max_length=255, blank=True, null=True)
    personal_phone = models.CharField(max_length=20, blank=True, null=True)
    work_phone = models.CharField(max_length=20, blank=True, null=True)
    personal_email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    office_location = models.ForeignKey(OfficeDetails, on_delete=models.CASCADE, null=True)
    role = models.CharField(max_length=255, choices=ROLES_CHOICE)
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="Supervisor_Or_Manager", null=True,
                                   blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # leave types
    sick_leave = models.FloatField(default=7.0)
    casual_leave = models.FloatField(default=8.0)
    earned_leave = models.FloatField(default=5.0)

    @property
    def LEAVE_LIMITS(self):
        """Property that returns dictionary from FloatFields."""
        return {
            "sick": self.sick_leave,
            "casual": self.casual_leave,
            "earned": self.earned_leave,
        }

    # Leave Summary
    def get_leave_summary(self):
        summary = {}
        approved_leaves = self.leave_records.filter(status="approved")
        total_taken = 0

        for leave_type, allotted in self.LEAVE_LIMITS.items():
            leaves = approved_leaves.filter(leave_type=leave_type)
            taken = sum(leave.duration for leave in leaves)
            remaining = allotted - taken

            summary[leave_type] = {
                "allotted": allotted,
                "taken": taken,
                "remaining": remaining,
            }
            total_taken += taken

        summary["total_remaining"] = sum(self.LEAVE_LIMITS.values()) - total_taken
        summary["total_taken"] = total_taken
        return summary

    def __str__(self):
        return self.user.username


# Leave model
class Leave(models.Model):
    LEAVE_TYPES = [
        ("sick", "Sick Leave"),
        ("casual", "Casual Leave"),
        ("earned", "Earned Leave"),
    ]

    STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_records"
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    # my change
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def duration(self):
        return (self.end_date - self.start_date).days + 1

    def total_days(self):
        return self.duration

    def __str__(self):
        return f"{self.employee} - {self.leave_type}"

    def __str__(self):
        return f"{self.employee} - {self.leave_type}"


class Product(models.Model):
    item_name = models.CharField(max_length=300)
    unit = models.CharField(max_length=30)
    short_code = models.CharField(max_length=10)
    hsn_code = models.CharField(max_length=10)
    item_description = models.CharField(max_length=500)

    def __str__(self):
        return f"{self.item_name} ({self.short_code})"


class Invoice(models.Model):
    INVOICE_STATUS = [
        ('DRAFT', 'Draft'),
        ('OPEN', 'Open'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='invoices')
    services = models.ManyToManyField(Task, blank=True, related_name='tagged_invoices')
    due_date = models.DateField()
    invoice_date = models.DateTimeField(default=timezone.now)
    subject = models.CharField(max_length=255)
    invoice_status = models.CharField(max_length=20, choices=INVOICE_STATUS, default="DRAFT")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.client.client_name}"


class InvoiceItem(models.Model):
    GST_CHOICES = [
        (0, '0%'),
        (5, '5%'),
        (12, '12%'),
        (18, '18%'),
        (28, '28%'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    unit_cost = models.FloatField()
    discount = models.FloatField(default=0.0)
    taxable_value = models.FloatField(editable=False)
    gst_percentage = models.IntegerField(choices=GST_CHOICES, default=0)
    net_total = models.FloatField(editable=False)

    def save(self, *args, **kwargs):
        # Logic: taxable_value = unit_cost - discount
        self.taxable_value = float(self.unit_cost) - float(self.discount)

        # Logic: net_total = taxable_value + gst %
        gst_amount = self.taxable_value * (self.gst_percentage / 100.0)
        self.net_total = self.taxable_value + gst_amount

        super().save(*args, **kwargs)

    def unit_cost_after_gst(self):
        gst_value = self.taxable_value * (self.gst_percentage / 100)
        return self.taxable_value - gst_value

    def __str__(self):
        return f"{self.product.item_name} - {self.invoice}"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CHECK', 'Check'),
        ('UPI', 'UPI'),
        ('BANK', 'Bank Transfer'),
    ]
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('UNPAID', 'Unpaid'),
        ('CANCELED', 'Canceled'),
    ]
    APPROVAL_STATUS = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    # Auto-compute fields
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="payments_created")
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default='PENDING')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="approved_payments")
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.id} for Invoice #{self.invoice.id}"


class Message(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('received', 'Received'),
    ]
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    is_seen = models.BooleanField(default=False)

    def __str__(self):
        return f"From{self.sender} to {self.receiver} - {self.status}"