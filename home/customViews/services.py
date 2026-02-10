from django.shortcuts import render, redirect
from django import forms
from django.shortcuts import render, get_object_or_404
from home.models import Service
from home.models import Product, Task, Invoice


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

    edit_service = None
    if 'edit' in request.GET:
        edit_service = get_object_or_404(Product, id=request.GET.get('edit'))
        form = ProductForm(instance=edit_service)
    else:
        form = ProductForm()

    if request.method == "POST":
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
    })


def delete_service(request, service_id):
    service = get_object_or_404(Product, id=service_id)
    service.delete()
    return redirect('list_services')


def service_details(request, service_id):
    # 1. Get the service (Product)
    service = get_object_or_404(Product, id=service_id)

    # 2. Get tasks that belong to this service (TEMP LOGIC)
    tasks = Task.objects.filter(service_type=service.item_name)

    # 3. Get invoices linked to those tasks
    invoices = Invoice.objects.filter(items__product=service).distinct()
    context = {
        "service": service,
        "invoices": invoices,
        "invoice_count": invoices.count(),
    }

    return render(request, "service_details.html", context)

