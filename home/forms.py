from django import forms
from .models import ClientDocumentUpload,DocumentRequest, DocumentMaster


class ClientDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ClientDocumentUpload
        fields = ('uploaded_file', 'remarks')

    def clean_uploaded_file(self):
        f = self.cleaned_data.get('uploaded_file')
        return f

class DocumentRequestForm(forms.ModelForm):
    documents = forms.ModelMultipleChoiceField(
        queryset=DocumentMaster.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input','id': 'tom-select-documents','multiple':'multiple'}),
        label="Select Documents to Request",
        required=True
    )

    class Meta:
        model = DocumentRequest
        fields = ['title', 'description', 'due_date', 'documents']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Request Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }