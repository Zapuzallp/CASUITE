from django import forms
from .models import Client


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
                field.widget.attrs.update({'class': 'form-control', 'rows': 2})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control'})

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
            'address_line1': forms.Textarea(attrs={'rows': 2}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }