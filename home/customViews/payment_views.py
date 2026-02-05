from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpResponseNotAllowed

from home.forms import PaymentCollectForm
from home.models import Invoice, Payment, Client
from home.utils import get_visible_payments, can_approve_payment, can_cancel_payment, get_invoice_totals


@login_required
def payment_list(request):

    # Payments listing
    # Get base queryset (visibility handled by utils.get_visible_payments)
    payments_qs = get_visible_payments(request.user).select_related('invoice__client', 'created_by', 'created_by__employee').order_by('-payment_date', '-id')

    # Accordion Filter
    q = request.GET.get('q', '').strip()
    client_id = request.GET.get('client_id')
    payment_status = request.GET.get('payment_status')
    approval_status = request.GET.get('approval_status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if q:
        filters = Q(invoice__client__client_name__icontains=q)
        if q.isdigit():
            filters |= Q(invoice_id=int(q))
        payments_qs = payments_qs.filter(filters)

    if client_id:
        payments_qs = payments_qs.filter(invoice__client__id=client_id)

    if payment_status:
        payments_qs = payments_qs.filter(payment_status=payment_status)

    if approval_status:
        payments_qs = payments_qs.filter(approval_status=approval_status)

    if date_from:
        payments_qs = payments_qs.filter(payment_date__gte=date_from)

    if date_to:
        payments_qs = payments_qs.filter(payment_date__lte=date_to)

    payments = list(payments_qs)

    # Provide recent invoices for modal
    invoices = Invoice.objects.filter(
        invoice_status__in=['OPEN', 'PARTIALLY_PAID']
    ).select_related('client').order_by('-id')[:200]
    # Annotate each page object with convenience flags used by template
    for p in payments:
        # safe getattr: created_by might be None
        p.creator_employee = getattr(p.created_by, 'employee', None)
        p.can_approve = can_approve_payment(request.user, p)
        p.can_cancel = can_cancel_payment(request.user, p)

    clients = Client.objects.order_by('client_name')

    context = {
        'payments': payments,
        'q': q,
        'clients': clients,
        'client_id': client_id,
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
    total_amount = paid_amount = balance_amount = Decimal('0.00')

    if invoice_id:
        invoice = get_object_or_404(Invoice, pk=invoice_id)
        total_amount, paid_amount, balance_amount = get_invoice_totals(invoice)

    if request.method == 'POST':
        form = PaymentCollectForm(
            request.POST,
            invoice_instance=invoice,
            balance_amount=balance_amount
        )
        if form.is_valid():
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.invoice = invoice
                payment.created_by = request.user
                payment.save()

            messages.success(request, "Payment recorded successfully.")
            return redirect('payment_detail', payment_id=payment.id)

        return render(request, 'payments/payment_collect.html', {
            'form': form,
            'invoice': invoice,
            'paid_amount': paid_amount,
            'total_amount': total_amount,
            'balance_amount': balance_amount,
        })

    # GET: prefill date to today
    initial = {'payment_date': timezone.now().date()}
    form = PaymentCollectForm(
        initial=initial,
        invoice_instance=invoice,
        balance_amount=balance_amount
    )

    return render(request, 'payments/payment_collect.html', {
        'form': form,
        'invoice': invoice,
        'paid_amount': paid_amount,
        'total_amount': total_amount,
        'balance_amount': balance_amount,
    })


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

    payment = get_object_or_404(
        qs.select_related('invoice__client', 'created_by', 'approved_by')
          .prefetch_related('invoice__items__product'),
        id=payment_id
    )

    invoice = payment.invoice

    invoice_total, invoice_paid, balance_amount = get_invoice_totals(invoice)

    context = {
        'payment': payment,
        'invoice_items': invoice.items.all(),
        'invoice_total': invoice_total,
        'invoice_paid': invoice_paid,
        'balance_amount': balance_amount,
    }

    return render(request, 'payments/payment_detail.html', context)
