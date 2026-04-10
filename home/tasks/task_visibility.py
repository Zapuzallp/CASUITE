from django.db.models import Q
from home.models import Task
from home.clients.client_access import get_accessible_clients


def get_visible_tasks(user):
    """
    CENTRALIZED TASK VISIBILITY LOGIC
    ---------------------------------
    This function defines which tasks are visible to a given user.
    It is the single source of truth and MUST be used across:
        - Task List View
        - Task Detail View
        - Delete / Update operations
        - Future APIs

    ----------------------------------------------------------------
    VISIBILITY RULES
    ----------------------------------------------------------------

    1. ADMIN (Superuser)
       - Full access to all tasks (no filtering applied)

    2. BRANCH MANAGER
       Can see:
       - Tasks linked to accessible clients (branch-based client access)
       - Tasks assigned to them
       - Tasks created by them
       - Tasks created by users in the same office_location

    3. STAFF / OTHER USERS
       Can see:
       - Tasks linked to accessible clients
       - Tasks assigned to them
       - Tasks created by them

    ----------------------------------------------------------------
    IMPORTANT NOTES
    ----------------------------------------------------------------
    - Uses `get_accessible_clients(user)` for client-level access control
    - Uses `office_location` (Employee model) for branch logic
    - Uses OR conditions intentionally to widen visibility where required
    - `.distinct()` is required due to ManyToMany (assignees)

    ----------------------------------------------------------------
    WARNING
    ----------------------------------------------------------------
    Do NOT duplicate this logic in views.
    Always use this function to avoid:
        - Inconsistent permissions
        - "Visible in list but not accessible" bugs
        - Future maintenance issues
    """

    # Base queryset with optimizations
    # 1. Initialize Base QuerySets
    # We select related fields to optimize database queries
    tasks_qs = Task.objects.select_related(
        'client', 'created_by'
    ).prefetch_related('assignees')

    # Get accessible clients (shared logic)
    # 2. Role-Based Visibility Logic
    # Fetch clients accessible to the user using universal role-based logic
    # (Admin → all, Branch Manager → branch + assigned, Staff → assigned only)
    clients_qs = get_accessible_clients(user)

    # Get employee safely (in case user has no employee record)
    employee = getattr(user, 'employee', None)

    # ---------------------------------------------------------
    # ADMIN → Full Access
    # ---------------------------------------------------------
    if user.is_superuser:
        return tasks_qs

    # ---------------------------------------------------------
    # BASE ACCESS (Common for all non-admin users)
    # ---------------------------------------------------------
    query = (
        Q(client__in=clients_qs) |   # Client-based access
        Q(assignees=user) |         # Direct assignment
        Q(created_by=user)          # Creator access
    )

    # ---------------------------------------------------------
    # BRANCH MANAGER → additional access (same office)
    # ---------------------------------------------------------
    if employee and employee.role == 'BRANCH_MANAGER':
        query |= Q(
            created_by__employee__isnull=False,
            created_by__employee__office_location_id=employee.office_location_id
        )

    # Final filtered queryset
    return tasks_qs.filter(query).distinct()