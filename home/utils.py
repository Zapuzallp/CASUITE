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
    - STAFF: sees only own payments (in same office)
    - ADMIN: sees payments created by staff under them AND their own payments (same office)
    - BRANCH_MANAGER: sees all payments in same office
    """
    from home.models import Payment, Employee

    if user.is_superuser:
        return Payment.objects.all()

    try:
        employee = user.employee
    except Employee.DoesNotExist:
        return Payment.objects.none()

    role = employee.role

    if role == 'STAFF':
        return Payment.objects.filter(created_by=user, created_by__employee__office_location=employee.office_location)

    if role == 'ADMIN':
        # payments created by users who report to this admin, plus admin's own payments
        staff_users = Employee.objects.filter(supervisor=user, office_location=employee.office_location).values_list('user', flat=True)
        user_list = list(staff_users) + [user]
        return Payment.objects.filter(created_by__in=user_list)

    if role == 'BRANCH_MANAGER':
        # All payments in same branch
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

    # Branch manager can approve anything in branch
    if approver.role == 'BRANCH_MANAGER':
        return True

    # Admin can approve staff under them
    if approver.role == 'ADMIN' and creator.supervisor == user:
        return True

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

    if actor.role == "ADMIN" and creator.supervisor == user and actor.office_location == creator.office_location:
        return True

    if actor.role == "BRANCH_MANAGER" and actor.office_location == creator.office_location:
        return True

    return False
