from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.views.decorators.http import require_POST

from home.forms import PaymentCollectForm
from home.models import Invoice, Payment, Client
from home.utils import get_visible_payments, can_approve_payment, can_cancel_payment, get_invoice_totals


@login_required
def payment_list(request):
    # Check if user is a partner (view-only access)
    is_partner = False
    if hasattr(request.user, 'employee'):
        is_partner = request.user.employee.role == 'PARTNER'

    # Payments listing
    # Get base queryset (visibility handled by utils.get_visible_payments)
    payments_qs = get_visible_payments(request.user).select_related('invoice__client', 'created_by',
                                                                    'created_by__employee',
                                                                    'created_by__employee__supervisor').order_by(
        '-payment_date', '-id')

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

    has_filters = any([
        q, client_id, payment_status,
        approval_status, date_from, date_to,
    ])

    paginator = Paginator(payments_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Determine if user has permission to Approve/Reject (Admins, Branch Managers, Superusers)
    # Partners cannot perform bulk actions
    show_bulk_actions = False
    if not is_partner:
        if request.user.is_superuser:
            show_bulk_actions = True
        elif hasattr(request.user, 'employee'):
            # Only ADMIN and BRANCH_MANAGER can perform bulk approvals/rejections
            if request.user.employee.role in ['ADMIN', 'BRANCH_MANAGER']:
                show_bulk_actions = True

    # Provide recent invoices for modal
    invoices = Invoice.objects.filter(
        invoice_status__in=['OPEN', 'PARTIALLY_PAID']
    ).select_related('client').order_by('-id')[:50]
    # Annotate each page object with convenience flags used by template
    for p in page_obj:
        # safe getattr: created_by might be None
        p.creator_employee = getattr(p.created_by, 'employee', None)
        p.can_approve = can_approve_payment(request.user, p) and not is_partner
        p.can_cancel = can_cancel_payment(request.user, p) and not is_partner

    clients = Client.objects.order_by('client_name')

    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'has_filters': has_filters,
        'q': q,
        'clients': clients,
        'client_id': client_id,
        'invoices': invoices,
        'show_bulk_actions': show_bulk_actions,
        'payment_status': payment_status,
        'approval_status': approval_status,
        'date_from': date_from,
        'date_to': date_to,
        'is_partner': is_partner,
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
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to collect payments.')
        return redirect('payment_list')

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
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to approve payments.')
        return redirect('payment_list')

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
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to reject payments.')
        return redirect('payment_list')

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
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to cancel payments.')
        return redirect('payment_list')

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
        payment.approval_status = 'CANCELED'
        payment.save(update_fields=['payment_status', 'approval_status'])
    messages.success(request, "Payment canceled.")
    return redirect('payment_list')


@login_required
def payment_detail(request, payment_id):
    # Check if user is a partner (view-only access)
    is_partner = False
    if hasattr(request.user, 'employee'):
        is_partner = request.user.employee.role == 'PARTNER'

    qs = get_visible_payments(request.user)

    payment = get_object_or_404(
        qs.select_related('invoice__client', 'created_by', 'approved_by')
        .prefetch_related('invoice__items__product'),
        id=payment_id
    )

    invoice = payment.invoice

    invoice_total, invoice_paid, balance_amount = get_invoice_totals(invoice)

    user_can_approve = can_approve_payment(request.user, payment) and not is_partner
    user_can_cancel = can_cancel_payment(request.user, payment) and not is_partner

    context = {
        'payment': payment,
        'invoice_items': invoice.items.all(),
        'invoice_total': invoice_total,
        'invoice_paid': invoice_paid,
        'balance_amount': balance_amount,
        'can_approve': user_can_approve,
        'can_cancel': user_can_cancel,
        'is_partner': is_partner,
    }

    return render(request, 'payments/payment_detail.html', context)


@login_required
@require_POST
def bulk_payment_action(request):
    """
    Handles bulk approval or rejection of payments.
    Expects POST data:
    - payment_ids: list of IDs
    - action: 'approve' or 'reject'
    """
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to perform bulk payment actions.')
        return redirect('payment_list')

    action = request.POST.get('action')
    payment_ids = request.POST.getlist('payment_ids')

    if not payment_ids or not action:
        messages.warning(request, "No payments selected or invalid action.")
        return redirect('payment_list')

    # Get payments that match IDs AND are visible to this user
    qs = get_visible_payments(request.user).filter(id__in=payment_ids)

    count = 0
    errors = 0

    with transaction.atomic():
        for payment in qs:
            # Only touch PENDING payments
            if payment.approval_status != 'PENDING':
                continue

            # Check Permissions per payment
            if not can_approve_payment(request.user, payment):
                errors += 1
                continue

            if action == 'approve':
                payment.approval_status = 'APPROVED'
                payment.payment_status = 'PAID'  # Assuming approval implies Paid
                payment.approved_by = request.user
                payment.approved_at = timezone.now()
                payment.save()
                count += 1

            elif action == 'reject':
                payment.approval_status = 'REJECTED'
                payment.payment_status = 'UNPAID'
                payment.save()
                count += 1

    if count > 0:
        messages.success(request, f"Successfully processed {count} payments.")

    if errors > 0:
        messages.warning(request, f"Skipped {errors} payments due to permission issues.")

    return redirect('payment_list')