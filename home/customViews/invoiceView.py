from django.views.generic import ListView
from django.views.generic.edit import FormMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from home.models import Invoice, Task, InvoiceItem
from home.forms import InvoiceForm, InvoiceItemForm
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages


class InvoiceListCreateView(LoginRequiredMixin, FormMixin, ListView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoice.html'
    context_object_name = 'invoices'
    success_url = reverse_lazy('invoice_all')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if 'invoice_form_errors' in self.request.session:
            form = self.form_class(self.request.session.get('invoice_form_data'))
            form._errors = self.request.session.pop('invoice_form_errors')
            self.request.session.pop('invoice_form_data', None)
            context['form'] = form
        else:
            context['form'] = self.get_form()

        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.status = "DRAFT"
            invoice.save()
            form.save_m2m()
            invoice.services.update(invoice_status=invoice.status)
            messages.success(request, "Invoice created successfully.")
            return redirect(self.success_url)

        return redirect(self.success_url)


@login_required
def load_tasks(request):
    client_id = request.GET.get('client')

    # 🔑 Guard: empty / invalid client
    if not client_id:
        return JsonResponse([], safe=False)

    tasks = (
        Task.objects
        .filter(client_id=client_id)
        .filter(tagged_invoices__isnull=True)
        .distinct()
        .values('id', 'task_title')
    )

    return JsonResponse(list(tasks), safe=False)
@login_required
def add_invoice_item_ajax(request, pk):
    invoice = Invoice.objects.get(pk=pk)

    if request.method == 'POST':
        form = InvoiceItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.invoice = invoice
            item.save()
            return JsonResponse({
                'product': str(item.product),
                'unit_cost': item.unit_cost,
                'discount': item.discount,
                'gst_percentage': item.gst_percentage,
                'taxable': round(item.taxable_value, 2),
                'unit_cost_after_gst_addition': round(item.unit_cost_after_gst_addition, 2),
                'total': round(item.net_total, 2),
            })


    return JsonResponse({'error': 'Invalid'}, status=400)

@login_required
def invoice_item_delete(request, item_id):
    if request.method == "POST":
        item = InvoiceItem.objects.get(pk=item_id)
        item.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)

@login_required
def approve_invoice(request, invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)

    invoice.services.filter(invoice_status="DRAFT").update(invoice_status="INVOICED")
    return redirect('invoice_details', invoice.invoice_id)

@login_required
def invoice_details(request, invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    #invoice_items = InvoiceItem.objects.all()

    # Get all tasks of this invoice's client
    client_tasks = Task.objects.filter(client=invoice.client)

    # Calculate total agreed fees from tasks
    total_task_fees = sum(
        task.agreed_fee or 0 for task in client_tasks
    )

    # Calculate invoice item totals
    invoice_item_total = sum(
        item.net_total for item in invoice.items.all()
    )

    item_form = InvoiceItemForm()

    return render(request, 'invoice_details.html', {
        'invoice': invoice,
    #'invoice_items': invoice_items
        'item_form': item_form,
        'client_tasks': client_tasks,
        'total_task_fees': total_task_fees,
        'invoice_item_total': invoice_item_total,
    })