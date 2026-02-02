from django.db.models import Q
from home.models import Client, Employee

def get_accessible_clients(user):
    """
    Returns a queryset of clients accessible to the given user based on role.
    """
    qs = Client.objects.select_related('office_location', 'assigned_ca', 'business_profile')

    if user.is_superuser:
        return qs

    try:
        employee = user.employee

        if employee.role == 'ADMIN':
            return qs

        elif employee.role == 'BRANCH_MANAGER':
            if employee.office_location:
                return qs.filter(
                    Q(office_location=employee.office_location) | Q(assigned_ca=user)
                )
            else:
                # Fallback if no office linked
                return qs.none()

        else:
            # STAFF or future roles
            return qs.filter(assigned_ca=user)

    except Employee.DoesNotExist:
        # User exists but has no Employee profile (edge case)
        return qs.filter(assigned_ca=user)
