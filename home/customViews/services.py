from django.shortcuts import render, redirect
from django import forms
from home.models import Product
from django.shortcuts import get_object_or_404


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'item_name',
            'unit',
            'short_code',
            'hsn_code',
            'item_description'
        ]
        widgets = {
            'item_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Service name'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Unit'
            }),
            'short_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Short code'
            }),
            'hsn_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HSN Code'
            }),
            'item_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Service description'
            }),
        }


def list_services(request):
    services = Product.objects.all().order_by('item_name')

    # Check if user is a partner (view-only access)
    is_partner = False
    if hasattr(request.user, 'employee'):
        is_partner = request.user.employee.role == 'PARTNER'

    edit_service = None
    if 'edit' in request.GET:
        # Block edit for partners
        if is_partner:
            from django.contrib import messages
            messages.error(request, 'You do not have permission to edit services.')
            return redirect('list_services')

        edit_service = get_object_or_404(Product, id=request.GET.get('edit'))
        form = ProductForm(instance=edit_service)
    else:
        form = ProductForm()

    if request.method == "POST":
        # Block POST for partners
        if is_partner:
            from django.contrib import messages
            messages.error(request, 'You do not have permission to modify services.')
            return redirect('list_services')

        service_id = request.POST.get('service_id')
        if service_id:
            service = get_object_or_404(Product, id=service_id)
            form = ProductForm(request.POST, instance=service)
        else:
            form = ProductForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('list_services')

    return render(request, 'list_services.html', {
        'services': services,
        'form': form,
        'edit_service': edit_service,
        'is_partner': is_partner,
    })


def delete_service(request, service_id):
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        from django.contrib import messages
        messages.error(request, 'You do not have permission to delete services.')
        return redirect('list_services')

    service = get_object_or_404(Product, id=service_id)
    service.delete()
    return redirect('list_services')