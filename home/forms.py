from django import forms
from .models import ClientDocumentUpload
from django import forms

from .models import ClientDocumentUpload


class ClientDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ClientDocumentUpload
        fields = ('uploaded_file', 'remarks')

    def clean_uploaded_file(self):
        f = self.cleaned_data.get('uploaded_file')
        return f
from crispy_forms.helper import FormHelper
from .models import ClientDocumentUpload
from django import forms
from crispy_forms.helper import FormHelper
from django.core.exceptions import ValidationError
from .models import (
    ClientService, GSTDetails, ITRDetails, AuditDetails,
    IncomeTaxCaseDetails, GSTCaseDetails, Task
)
from datetime import date
from .models import ClientDocumentUpload


class ClientDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ClientDocumentUpload
        fields = ('uploaded_file', 'remarks')

    def clean_uploaded_file(self):
        f = self.cleaned_data.get('uploaded_file')
        return f



# -------------------------
# SERVICE ASSIGNMENT FORMS
# -------------------------

class ClientServiceForm(forms.ModelForm):
    """
    Form for basic client service assignment details
    Step 1 of service assignment wizard
    """

    class Meta:
        model = ClientService
        fields = ['start_date', 'end_date', 'billing_cycle', 'agreed_fee', 'remarks', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'billing_cycle': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'agreed_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'required': True
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional internal notes...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date and start_date < date.today():
            raise ValidationError("Start date cannot be in the past. Please select today's date or a future date.")
        return start_date

    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        start_date = self.cleaned_data.get('start_date')

        if end_date and start_date and end_date <= start_date:
            raise ValidationError("End date must be after the start date.")
        return end_date

    def clean_agreed_fee(self):
        agreed_fee = self.cleaned_data.get('agreed_fee')
        if agreed_fee is not None and agreed_fee <= 0:
            raise ValidationError("Agreed fee must be greater than 0.")
        return agreed_fee

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class TaskForm(forms.ModelForm):

    class Meta:
        model = Task
        required_css_class = 'required'
        fields = [
            'task_title',
            'period_from',
            'period_to',
            'due_date',
            'assigned_to',
            'recurrence',
            'remarks',
            'document_link',
        ]
        widgets = {
            'task_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter task title',
                'required': True,
                'minlength': '3',
                'maxlength': '255',
                'pattern': r'.{3,}',
                'title': 'Task title must be at least 3 characters long'
            }),
            'period_from': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'period_to': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True,
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control',
            }),
            'recurrence': forms.Select(attrs={
                'class': 'form-control',
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Task details or internal notes...'
            }),
            'document_link': forms.FileInput(attrs={
                'class': 'form-control',
            }),
        }


class GSTDetailsForm(forms.ModelForm):
    """
    Form for GST service specific details
    Used for GST Services in step 2 of wizard
    """

    class Meta:
        model = GSTDetails
        required_css_class = 'required'
        fields = [
            'gst_number', 'date_of_registration', 'type_of_registration',
            'gst_username', 'gst_password', 'principal_place_of_business',
            'filing_frequency', 'state_code', 'remarks'
        ]
        widgets = {
            'gst_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 22AAAAA0000A1Z5',
                'maxlength': '15',
                'minlength': '15',
                'pattern': r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
                'oninput': "this.value = this.value.toUpperCase().substring(0, 15);",
                'title': 'GST Number format: 22AAAAA0000A1Z5 (15 characters)',
                'required': True
            }),
            'date_of_registration': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'type_of_registration': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'gst_username': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'gst_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'principal_place_of_business': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'required': True
            }),
            'filing_frequency': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'state_code': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '2',
                'minlength': '2',
                'pattern': r'^[0-9]{2}$',
                'placeholder': 'e.g. 22',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '').substring(0, 2);",
                'title': 'State code: 2 digits (e.g., 22 for Chhattisgarh)',
                'inputmode': 'numeric',
                'required': True
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes...'
            })
        }

    def clean_gst_number(self):
        gst_number = self.cleaned_data.get('gst_number')
        if gst_number and len(gst_number) != 15:
            raise ValidationError("GST number must be exactly 15 characters long.")
        return gst_number

    def clean_state_code(self):
        state_code = self.cleaned_data.get('state_code')
        if state_code and not state_code.isdigit():
            raise ValidationError("State code must contain only digits.")
        return state_code


class ITRDetailsForm(forms.ModelForm):
    """
    Form for ITR service specific details
    Used for ITR Services in step 2 of wizard
    """

    class Meta:
        model = ITRDetails
        required_css_class = 'required'
        fields = [
            'pan_number', 'aadhaar_number', 'itr_type', 'assessment_year',
            'income_source', 'last_itr_ack_no', 'filing_mode', 'remarks'
        ]
        widgets = {
            'pan_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. AAAAA0000A',
                'maxlength': '10',
                'minlength': '10',
                'pattern': r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
                'oninput': "this.value = this.value.toUpperCase().substring(0, 10);",
                'title': 'PAN format: AAAAA0000A (10 characters)',
                'required': True
            }),
            'aadhaar_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 123456789012',
                'maxlength': '12',
                'minlength': '12',
                'pattern': r'^[0-9]{12}$',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '').substring(0, 12);",
                'title': 'Aadhaar format: 12 digits only (no spaces)',
                'inputmode': 'numeric'
            }),
            'itr_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'assessment_year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2024-25',
                'maxlength': '9',
                'required': True
            }),
            'income_source': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'required': True
            }),
            'last_itr_ack_no': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '50',
                'placeholder': 'Previous year acknowledgment number'
            }),
            'filing_mode': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes...'
            })
        }

    def clean_pan_number(self):
        pan_number = self.cleaned_data.get('pan_number')
        if pan_number and len(pan_number) != 10:
            raise ValidationError("PAN number must be exactly 10 characters long.")
        return pan_number.upper() if pan_number else pan_number

    def clean_assessment_year(self):
        assessment_year = self.cleaned_data.get('assessment_year')
        if assessment_year:
            import re
            if not re.match(r'^\d{4}-\d{2}$', assessment_year):
                raise ValidationError("Assessment year must be in format YYYY-YY (e.g., 2024-25)")
        return assessment_year


class AuditDetailsForm(forms.ModelForm):
    """
    Form for Audit service specific details
    Used for Audit Services in step 2 of wizard
    """

    class Meta:
        model = AuditDetails
        required_css_class = 'required'
        fields = [
            'audit_type', 'financial_year', 'auditor_name',
            'audit_start_date', 'audit_end_date', 'report_upload', 'remarks'
        ]
        widgets = {
            'audit_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'financial_year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2023-24',
                'maxlength': '9',
                'required': True
            }),
            'auditor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'required': True
            }),
            'audit_start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'audit_end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'report_upload': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes...'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('audit_start_date')
        end_date = cleaned_data.get('audit_end_date')

        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError("Audit end date must be after start date.")

        return cleaned_data


class IncomeTaxCaseForm(forms.ModelForm):
    """
    Form for Income Tax Case details
    Used for Income Tax Case Services in step 2 of wizard
    """

    class Meta:
        model = IncomeTaxCaseDetails
        required_css_class = 'required'
        fields = [
            'case_type', 'notice_number', 'notice_date', 'ao_name',
            'ward_circle', 'status', 'last_hearing_date', 'next_hearing_date',
            'documents_link', 'remarks'
        ]
        widgets = {
            'case_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'notice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100'
            }),
            'notice_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'ao_name': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'required': True
            }),
            'ward_circle': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'last_hearing_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'next_hearing_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'documents_link': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.png'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Case specific notes...'
            })
        }


class GSTCaseForm(forms.ModelForm):
    """
    Form for GST Case details
    Used for GST Case Services in step 2 of wizard
    """

    class Meta:
        model = GSTCaseDetails
        required_css_class = 'required'
        fields = [
            'case_type', 'gstin', 'case_number', 'date_of_notice',
            'officer_name', 'jurisdiction', 'status', 'remarks'
        ]
        widgets = {
            'case_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'gstin': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '15',
                'minlength': '15',
                'pattern': r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
                'placeholder': 'e.g. 22AAAAA0000A1Z5',
                'oninput': "this.value = this.value.toUpperCase().substring(0, 15);",
                'title': 'GSTIN format: 22AAAAA0000A1Z5 (15 characters)',
                'required': True
            }),
            'case_number': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'required': True
            }),
            'date_of_notice': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True
            }),
            'officer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'required': True
            }),
            'jurisdiction': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Case specific notes...'
            })
        }

    def clean_gstin(self):
        gstin = self.cleaned_data.get('gstin')
        if gstin and len(gstin) != 15:
            raise ValidationError("GSTIN must be exactly 15 characters long.")
        return gstin.upper() if gstin else gstin
