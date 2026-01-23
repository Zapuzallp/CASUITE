from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, HttpResponseNotAllowed

from home.forms import PaymentCollectForm
from home.models import Invoice, Payment
from home.utils import get_visible_payments, can_approve_payment, can_cancel_payment


@login_required
def payment_list(request):
    """
    Payments listing — simple search (invoice id or client name) + pagination.
    """
    # Get base queryset (visibility handled by utils.get_visible_payments)
    qs = get_visible_payments(request.user).select_related('invoice__client', 'created_by', 'created_by__employee').order_by('-payment_date', '-id')

    # Search q: invoice id OR client name
    q = request.GET.get('q', '').strip()
    if q:
        filters = Q(invoice__client__client_name__icontains=q)
        if q.isdigit():
            filters |= Q(invoice_id=int(q))
        qs = qs.filter(filters)

    # Pagination
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Provide recent invoices for modal
    invoices = Invoice.objects.select_related('client').order_by('-id')[:200]

    # Annotate each page object with convenience flags used by template
    for p in page_obj:
        # safe getattr: created_by might be None
        p.creator_employee = getattr(p.created_by, 'employee', None)
        p.can_approve = can_approve_payment(request.user, p)
        p.can_cancel = can_cancel_payment(request.user, p)

    context = {
        'payments': page_obj,
        'q': q,
        'invoices': invoices,
        # template sometimes references emp (current user's employee)
        'emp': getattr(request.user, 'employee', None),
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
        qid = request.GET.get('invoice_id')
        if qid:
            invoice = get_object_or_404(Invoice, pk=qid)

    if request.method == 'POST':
        form = PaymentCollectForm(request.POST, invoice_instance=invoice)
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    # attach invoice
                    payment.invoice = invoice or payment.invoice
                    # audit
                    payment.created_by = request.user
                    payment.save()
                messages.success(request, "Payment recorded successfully.")
                return redirect('payment_list')
            except Exception as exception:
                messages.error(request, "Could not save payment. Try again or contact admin.")
        return render(request, 'payments/payment_collect.html', {'form': form, 'invoice': invoice})

    # GET: prefill date to today
    initial = {'payment_date': timezone.now().date()}
    form = PaymentCollectForm(initial=initial, invoice_instance=invoice)
    return render(request, 'payments/payment_collect.html', {'form': form, 'invoice': invoice})


@login_required
def approve_payment(request, payment_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    payment = get_object_or_404(Payment, id=payment_id)
    if payment.approval_status != 'PENDING' or payment.payment_status != 'PENDING':
        messages.error(request, "This payment cannot be approved.")
        return redirect('payment_list')
    if not can_approve_payment(request.user, payment):
        return HttpResponseForbidden("You are not authorized to approve this payment.")
    with transaction.atomic():
        payment.approval_status = 'APPROVED'
        payment.payment_status = 'PAID'
        payment.approved_by = request.user
        payment.approved_at = timezone.now()
        payment.save()
    messages.success(request, "Payment approved successfully.")
    return redirect('payment_list')


@login_required
def reject_payment(request, payment_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    payment = get_object_or_404(Payment, id=payment_id)
    if payment.approval_status != 'PENDING' or payment.payment_status != 'PENDING':
        messages.error(request, "This payment cannot be rejected.")
        return redirect('payment_list')
    if not can_approve_payment(request.user, payment):
        return HttpResponseForbidden("You are not authorized to reject this payment.")
    with transaction.atomic():
        payment.approval_status = 'REJECTED'
        payment.payment_status = 'UNPAID'
        payment.approved_by = request.user
        payment.approved_at = timezone.now()
        payment.save()
    messages.success(request, "Payment rejected.")
    return redirect('payment_list')


@login_required
def cancel_payment(request, payment_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    payment = get_object_or_404(Payment, id=payment_id)
    if payment.approval_status != 'PENDING' or payment.payment_status != 'PENDING':
        messages.error(request, "This payment cannot be canceled.")
        return redirect('payment_list')
    # Use utility function to centralize logic
    if not can_cancel_payment(request.user, payment):
        return HttpResponseForbidden("You are not allowed to cancel this payment.")
    with transaction.atomic():
        payment.payment_status = 'CANCELED'
        payment.save(update_fields=['payment_status'])
    messages.success(request, "Payment canceled.")
    return redirect('payment_list')


@login_required
def payment_detail(request, payment_id):
    qs = get_visible_payments(request.user)
    payment = get_object_or_404(qs.select_related('invoice__client', 'created_by', 'approved_by'), id=payment_id)
    return render(request, 'payments/payment_detail.html', {'payment': payment})
