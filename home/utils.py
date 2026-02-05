def generate_file_number(office_location):
    """
    Generates a unique file number based on office location.
    Example: KO000001, KO000002
    """

    from home.models import Client

    # Office code (first 2 letters)
    office_code = office_location.office_name[:2].upper()

    # Get latest client for this office having file_number
    last_client = (
        Client.objects
        .filter(
            office_location=office_location,
            file_number__startswith=office_code
        )
        .order_by('-file_number')
        .first()
    )

    if last_client and last_client.file_number:
        # Extract numeric part
        last_number = int(last_client.file_number.replace(office_code, ''))
        next_number = last_number + 1
    else:
        # First client for this office
        next_number = 1

    return f"{office_code}{str(next_number).zfill(6)}"

def get_visible_payments(user):
    """
    Returns a queryset of payments the given user is allowed to see.
    - superuser: sees all
    - STAFF: sees only own payments
    - BRANCH_MANAGER: sees payments created by staff under them AND their own payments
    - ADMIN: sees all payments in same office
    """
    from home.models import Payment, Employee
    from django.db.models import Q

    if user.is_superuser:
        return Payment.objects.all()

    try:
        employee = user.employee
    except Employee.DoesNotExist:
        return Payment.objects.none()

    role = employee.role

    if role == 'STAFF':
        return Payment.objects.filter(created_by=user, created_by__employee__office_location=employee.office_location)

    if role == 'BRANCH_MANAGER':
        # Branch Manager sees own + staff under him

        staff_users = Employee.objects.filter(supervisor=user).values_list('user', flat=True)
        return Payment.objects.filter(
            Q(created_by=user) | Q(created_by__in=staff_users)
        )

    if role == 'ADMIN':
        # Admin can see all payments in branch
        return Payment.objects.filter(created_by__employee__office_location=employee.office_location)

    return Payment.objects.none()

def can_approve_payment(user, payment):
    try:
        approver = user.employee
        creator = payment.created_by.employee
    except Exception:
        return False

    # Must be same branch
    if approver.office_location != creator.office_location:
        return False

    # Admin can approve any payment
    if approver.role == 'ADMIN':
        return approver.office_location == creator.office_location

    # Branch manager can approve only their own payments
    if approver.role == 'BRANCH_MANAGER':
        return (
            payment.created_by == user or
            creator.supervisor == user
        )

    return False

def can_cancel_payment(user, payment):
    try:
        actor = user.employee
        creator = payment.created_by.employee
    except Exception:
        return False

    if payment.approval_status != "PENDING" or payment.payment_status != "PENDING":
        return False

    if payment.created_by == user:
        return True

    if actor.role == "ADMIN":
        return actor.office_location == creator.office_location

    if actor.role == "BRANCH_MANAGER":
        return (
            payment.created_by == user or
            creator.supervisor == user
        )

    return False

from django.db.models import Sum
from decimal import Decimal

def get_invoice_totals(invoice):
    total_amount = invoice.items.aggregate(
        total=Sum('net_total')
    )['total'] or Decimal('0.00')

    total_paid = invoice.payments.filter(
        payment_status='PAID',
        approval_status='APPROVED'
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    balance = total_amount - total_paid

    return total_amount, total_paid, balance