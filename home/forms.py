from django import forms
from .models import Client, CompanyDetails, LLPDetails, OPCDetails, Section8CompanyDetails, HUFDetails, ClientDocumentUpload

class ClientDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ClientDocumentUpload
        fields = ('uploaded_file', 'remarks')

    def clean_uploaded_file(self):
        f = self.cleaned_data.get('uploaded_file')
        return f

class ClientForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all form fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 1})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control'})

            # Add placeholder for better UX
            if field_name in ['client_name', 'primary_contact_name', 'pan_no', 'email']:
                field.widget.attrs.update({'placeholder': f'Enter {field.label.lower()}'})

    class Meta:
        model = Client
        fields = [
            'client_name',
            'primary_contact_name',
            'pan_no',
            'email',
            'phone_number',
            'address_line1',
            'aadhar',
            'city',
            'state',
            'postal_code',
            'country',
            'date_of_engagement',
            'assigned_ca',
            'client_type',
            'business_structure',
            'status',
            'remarks',
            'din_no'
        ]
        widgets = {
            'date_of_engagement': forms.DateInput(attrs={'type': 'date'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter complete address'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter any additional remarks'}),
            'pan_no': forms.TextInput(attrs={'placeholder': 'e.g., ABCDE1234F', 'style': 'text-transform: uppercase'}),
            'aadhar': forms.TextInput(attrs={'placeholder': 'e.g., 1234 5678 9012'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'e.g., +91 9876543210'}),
        }

    def clean_pan_no(self):
        pan_no = self.cleaned_data.get('pan_no', '').upper().strip()
        if len(pan_no) != 10:
            raise forms.ValidationError("PAN number must be exactly 10 characters long.")
        return pan_no

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        # Basic phone number validation
        if len(phone_number) < 10:
            raise forms.ValidationError("Phone number must be at least 10 digits long.")
        return phone_number


class CompanyDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = CompanyDetails
        fields = [
            'company_type',
            'proposed_company_name',
            'cin',
            'authorised_share_capital',
            'paid_up_share_capital',
            'number_of_directors',
            'number_of_shareholders',
            'registered_office_address',
            'date_of_incorporation',
            'udyam_registration',
            'directors',
            'moa_file',
            'aoa_file'
        ]
        widgets = {
            'registered_office_address': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete registered office address'}),
            'proposed_company_name': forms.TextInput(attrs={'placeholder': 'Enter proposed company name'}),
            'cin': forms.TextInput(attrs={'placeholder': 'Enter Corporate Identification Number'}),
            'authorised_share_capital': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'paid_up_share_capital': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'udyam_registration': forms.TextInput(attrs={'placeholder': 'Enter Udyam registration number'}),
        }


class LLPDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = LLPDetails
        fields = [
            'llp_name',
            'llp_registration_no',
            'registered_office_address_llp',
            'designated_partners',
            'paid_up_capital_llp',
            'date_of_registration_llp',
            'llp_agreement_file'
        ]
        widgets = {
            'registered_office_address_llp': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete registered office address'}),
            'llp_name': forms.TextInput(attrs={'placeholder': 'Enter LLP name'}),
            'llp_registration_no': forms.TextInput(attrs={'placeholder': 'Enter LLP registration number'}),
            'paid_up_capital_llp': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }


class OPCDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})

    class Meta:
        model = OPCDetails
        fields = [
            'opc_name',
            'opc_cin',
            'registered_office_address_opc',
            'sole_member_name',
            'nominee_member_name',
            'paid_up_share_capital_opc',
            'date_of_incorporation_opc'
        ]
        widgets = {
            'registered_office_address_opc': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete registered office address'}),
            'opc_name': forms.TextInput(attrs={'placeholder': 'Enter OPC name'}),
            'opc_cin': forms.TextInput(attrs={'placeholder': 'Enter OPC CIN'}),
            'nominee_member_name': forms.TextInput(attrs={'placeholder': 'Enter nominee member name'}),
            'paid_up_share_capital_opc': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }


class Section8CompanyDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})

    class Meta:
        model = Section8CompanyDetails
        fields = [
            'section8_company_name',
            'registration_no_section8',
            'registered_office_address_s8',
            'object_clause',
            'whether_licence_obtained',
            'date_of_registration_s8'
        ]
        widgets = {
            'registered_office_address_s8': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete registered office address'}),
            'section8_company_name': forms.TextInput(attrs={'placeholder': 'Enter Section 8 company name'}),
            'registration_no_section8': forms.TextInput(attrs={'placeholder': 'Enter registration number'}),
            'object_clause': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'Describe the main objectives and purposes of the company'}),
        }


class HUFDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = HUFDetails
        fields = [
            'huf_name',
            'pan_huf',
            'date_of_creation',
            'karta_name',
            'number_of_coparceners',
            'number_of_members',
            'residential_address',
            'bank_account_details',
            'deed_of_declaration_file',
            'business_activity',
            'remarks'
        ]
        widgets = {
            'residential_address': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete residential address'}),
            'huf_name': forms.TextInput(attrs={'placeholder': 'Enter HUF name'}),
            'pan_huf': forms.TextInput(attrs={'placeholder': 'e.g., ABCDE1234F', 'style': 'text-transform: uppercase'}),
            'bank_account_details': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter bank details in JSON format: {"bank_name": "", "account_number": "", "ifsc_code": ""}'
            }),
            'business_activity': forms.TextInput(attrs={'placeholder': 'Enter main business activity'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter any additional remarks'}),
            'number_of_coparceners': forms.NumberInput(attrs={'min': '1'}),
            'number_of_members': forms.NumberInput(attrs={'min': '1'}),
        }

    def clean_pan_huf(self):
        pan_huf = self.cleaned_data.get('pan_huf', '').upper().strip()
        if len(pan_huf) != 10:
            raise forms.ValidationError("HUF PAN number must be exactly 10 characters long.")
        return pan_huf

    def clean_bank_account_details(self):
        bank_details = self.cleaned_data.get('bank_account_details', '').strip()
        # Basic JSON validation
        if bank_details:
            try:
                import json
                parsed = json.loads(bank_details)
                if not isinstance(parsed, dict):
                    raise forms.ValidationError("Bank details must be a valid JSON object.")
            except json.JSONDecodeError:
                raise forms.ValidationError("Please enter valid JSON format for bank details.")
        return bank_details