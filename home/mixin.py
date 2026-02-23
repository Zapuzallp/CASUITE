from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages


class AdminAccessMixin(UserPassesTestMixin):
    """Reusable Mixin to restrict access to Admins and Superusers"""

    def test_func(self):
        user = self.request.user
        return user.is_superuser or (
                hasattr(user, 'employee') and (user.employee.role == 'ADMIN' or user.employee.role == 'BRANCH_MANAGER')
        )

    def handle_no_permission(self):
        """Custom behavior when test_func returns False"""
        messages.error(self.request, "You don't have permission to view this page.")
        return redirect('/')