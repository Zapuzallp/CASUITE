from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator

from home.forms import PaymentCollectForm
from home.models import Invoice, Payment

@login_required
def payment_list(request):
    """
    Payments listing — simple search (invoice id or client name) + pagination.
    Provides 'invoices' for the modal.
    """
    qs = Payment.objects.select_related('invoice__client', 'created_by').order_by('-payment_date', '-id')

    # Non-staff sees only their own created payments
    if not request.user.is_staff:
        qs = qs.filter(created_by=request.user)

    q = request.GET.get('q', '').strip()
    if q:
        filters = Q(invoice__client__client_name__icontains=q)
        if q.isdigit():
            filters |= Q(invoice_id=int(q))
        qs = qs.filter(filters)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Provide recent invoices for modal (limit for performance)
    invoices = Invoice.objects.select_related('client').order_by('-id')[:200]

    context = {
        'payments': page_obj,
        'q': q,
        'invoices': invoices,
    }
    return render(request, 'payments/payment_list.html', context)

@login_required
def payment_collect(request, invoice_id=None):
    """
    GET/POST for /payment/<invoice_id>/collect/
    Uses PaymentCollectForm(invoice_instance=invoice) so invoice can be locked.
    """
    invoice = None
    if invoice_id:
        invoice = get_object_or_404(Invoice, pk=invoice_id)
    else:
        # fallback to ?invoice_id= for legacy links
        qid = request.GET.get('invoice_id')
        if qid:
            invoice = get_object_or_404(Invoice, pk=qid)

    if request.method == 'POST':
        form = PaymentCollectForm(request.POST, invoice_instance=invoice)
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    # attach invoice (defensive)
                    payment.invoice = invoice or payment.invoice
                    # audit
                    payment.created_by = request.user
                    payment.save()
                messages.success(request, "Payment recorded successfully.")
                return redirect('payment_list')
            except Exception as exc:
                # keep message friendly; log exc in real app
                messages.error(request, "Could not save payment. Try again or contact admin.")
        # if invalid, fall through to render with errors
        return render(request, 'payments/payment_collect.html', {'form': form, 'invoice': invoice})

    # GET: prefill date to today
    initial = {'payment_date': timezone.now().date()}
    form = PaymentCollectForm(initial=initial, invoice_instance=invoice)
    return render(request, 'payments/payment_collect.html', {'form': form, 'invoice': invoice})
