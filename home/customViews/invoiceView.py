from django.views.generic import ListView
from django.views.generic.edit import FormMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.utils import timezone
from home.models import Invoice, Task, InvoiceItem
from home.forms import InvoiceForm, InvoiceItemForm
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from home.clients.client_access import get_accessible_clients


class InvoiceListCreateView(LoginRequiredMixin, FormMixin, ListView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'payments/invoice_list.html'
    context_object_name = 'invoices'
    success_url = reverse_lazy('invoice_all')

    def get_queryset(self):
        """Filter invoices based on user role and access"""
        if self.request.user.is_superuser:
            qs = Invoice.objects.all()
        else:
            accessible_clients = get_accessible_clients(self.request.user)
            qs = Invoice.objects.filter(client__in=accessible_clients)

        qs = qs.select_related('client').prefetch_related('payments').order_by('-invoice_date', '-id')

        # Apply filters
        client_filter = self.request.GET.get('client', '').strip()
        status_filter = self.request.GET.get('status', '').strip()
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()
        search = self.request.GET.get('search', '').strip()

        if client_filter:
            qs = qs.filter(client_id=client_filter)

        if date_from:
            qs = qs.filter(invoice_date__gte=date_from)

        if date_to:
            qs = qs.filter(invoice_date__lte=date_to)

        if search:
            filters = Q(subject__icontains=search) | Q(client__client_name__icontains=search)
            if search.isdigit():
                filters |= Q(id=int(search))
            qs = qs.filter(filters)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if 'invoice_form_errors' in self.request.session:
            form = self.form_class(self.request.session.get('invoice_form_data'))
            form._errors = self.request.session.pop('invoice_form_errors')
            self.request.session.pop('invoice_form_data', None)
            context['form'] = form
        else:
            context['form'] = self.get_form()

        # Add invoice data for template
        payment_status_filter = self.request.GET.get('payment_status', '').strip()
        due_status_filter = self.request.GET.get('due_status', '').strip()

        invoices_data = []
        today = timezone.now().date()

        for inv in self.get_queryset():
            # Calculate total_paid from payments
            from decimal import Decimal
            total_paid = inv.payments.filter(payment_status='PAID').aggregate(
                total=Sum('amount'))['total'] or Decimal('0')

            # Calculate total_amount from invoice items (convert to Decimal)
            total_amount_raw = inv.items.aggregate(total=Sum('net_total'))['total'] or 0
            total_amount = Decimal(str(total_amount_raw))

            balance = total_amount - total_paid

            # Calculate Payment Status (business status)
            if inv.invoice_status == 'DRAFT':
                payment_status = 'DRAFT'
                payment_status_display = 'Draft'
            elif total_paid == 0:
                payment_status = 'OPEN'
                payment_status_display = 'Open'
            elif total_paid >= total_amount:
                payment_status = 'PAID'
                payment_status_display = 'Paid'
            else:
                payment_status = 'PARTIALLY_PAID'
                payment_status_display = 'Partially Paid'

            # Calculate Due Status (time-based status)
            # Only show due status for Open and Partially Paid invoices
            due_status = None
            if payment_status in ['OPEN', 'PARTIALLY_PAID'] and inv.due_date:
                if inv.due_date < today:
                    due_status = 'overdue'
                elif inv.due_date == today:
                    due_status = 'due_today'
                else:
                    due_status = 'not_due'

            # Check if invoice has any payments
            has_payments = inv.payments.filter(payment_status='PAID').exists()

            # Apply payment status filter
            if payment_status_filter and payment_status != payment_status_filter:
                continue

            # Apply due status filter
            if due_status_filter:
                if due_status_filter == 'not_due' and due_status != 'not_due':
                    continue
                elif due_status_filter == 'due_today' and due_status != 'due_today':
                    continue
                elif due_status_filter == 'overdue' and due_status != 'overdue':
                    continue

            invoices_data.append({
                'invoice': inv,
                'total_amount': total_amount,
                'total_paid': total_paid,
                'balance': balance,
                'payment_status': payment_status,
                'payment_status_display': payment_status_display,
                'due_status': due_status,
                'has_payments': has_payments,
            })

        context['invoices'] = invoices_data
        context['clients'] = get_accessible_clients(self.request.user).order_by('client_name')
        context['filters'] = {
            'client': self.request.GET.get('client', ''),
            'payment_status': self.request.GET.get('payment_status', ''),
            'due_status': self.request.GET.get('due_status', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'search': self.request.GET.get('search', ''),
        }

        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.invoice_status = "DRAFT"
            invoice.save()
            form.save_m2m()
            # Note: Removed invoice_status update on services as Task model doesn't have this field
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
                'unit_cost_after_gst': round(item.unit_cost_after_gst(), 2),
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
def change_invoice_status(request, invoice_id):
    """
    Change invoice status between DRAFT and OPEN.
    Status is locked once payment is received.
    """
    if request.method == 'POST':
        invoice = Invoice.objects.get(pk=invoice_id)

        # Check if any payment has been received
        has_payment = invoice.payments.filter(payment_status='PAID').exists()

        if has_payment:
            messages.error(request, "Cannot change status - Payment has been received for this invoice.")
            return redirect('invoice_details', invoice_id)

        new_status = request.POST.get('invoice_status')

        # Only allow DRAFT and OPEN
        if new_status in ['DRAFT', 'OPEN']:
            invoice.invoice_status = new_status
            invoice.save()

            status_display = 'Draft' if new_status == 'DRAFT' else 'Open'
            messages.success(request, f"Invoice status changed to {status_display} successfully.")
        else:
            messages.error(request, "Invalid status selected.")

        return redirect('invoice_details', invoice_id)

    return redirect('invoice_details', invoice_id)


@login_required
def invoice_details(request, invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    # invoice_items = InvoiceItem.objects.all()

    # Get only tasks associated with THIS invoice (not all client tasks)
    client_tasks = invoice.services.all()

    # Calculate total agreed fees from tasks
    total_task_fees = sum(
        task.agreed_fee or 0 for task in client_tasks
    )

    # Calculate invoice item totals
    invoice_item_total = sum(
        item.net_total for item in invoice.items.all()
    )

    # Check if any payment has been received
    has_payments = invoice.payments.filter(payment_status='PAID').exists()

    # Calculate actual payment status based on payments
    from decimal import Decimal
    total_paid = invoice.payments.filter(payment_status='PAID').aggregate(
        total=Sum('amount'))['total'] or Decimal('0')

    # Calculate total_amount from invoice items (convert to Decimal)
    total_amount_raw = invoice.items.aggregate(total=Sum('net_total'))['total'] or 0
    total_amount = Decimal(str(total_amount_raw))

    balance = total_amount - total_paid

    # Determine actual payment status
    if invoice.invoice_status == 'DRAFT':
        actual_payment_status = 'DRAFT'
        payment_status_display = 'Draft'
    elif total_paid == 0:
        actual_payment_status = 'OPEN'
        payment_status_display = 'Open'
    elif total_paid >= total_amount:
        actual_payment_status = 'PAID'
        payment_status_display = 'Paid'
    else:
        actual_payment_status = 'PARTIALLY_PAID'
        payment_status_display = 'Partially Paid'

    item_form = InvoiceItemForm()

    return render(request, 'invoice_details.html', {
        'invoice': invoice,
        # 'invoice_items': invoice_items
        'item_form': item_form,
        'client_tasks': client_tasks,
        'total_task_fees': total_task_fees,
        'invoice_item_total': invoice_item_total,
        'has_payments': has_payments,
        'actual_payment_status': actual_payment_status,
        'payment_status_display': payment_status_display,
        'balance': balance,
    })


@login_required
def invoice_bulk_status_update(request):
    """
    Bulk update invoice statuses from the invoice list table.
    Only updates invoices that are DRAFT or OPEN and have no payments.
    """
    if request.method == 'POST':
        updated_count = 0
        locked_count = 0

        for key, value in request.POST.items():
            if key.startswith('status_'):
                invoice_id = key.replace('status_', '')
                new_status = value

                try:
                    invoice = Invoice.objects.get(pk=invoice_id)

                    # Check if any payment has been received
                    has_payment = invoice.payments.filter(payment_status='PAID').exists()

                    if has_payment:
                        locked_count += 1
                        continue

                    # Only allow DRAFT and OPEN
                    if new_status in ['DRAFT', 'OPEN'] and invoice.invoice_status != new_status:
                        invoice.invoice_status = new_status
                        invoice.save()
                        updated_count += 1

                except Invoice.DoesNotExist:
                    continue

        if updated_count > 0:
            messages.success(request, f"Successfully updated {updated_count} invoice(s).")

        if locked_count > 0:
            messages.warning(request, f"{locked_count} invoice(s) could not be updated - Payment received.")

        if updated_count == 0 and locked_count == 0:
            messages.info(request, "No changes were made.")

    return redirect('invoice_list')