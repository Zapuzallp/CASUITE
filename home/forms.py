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
