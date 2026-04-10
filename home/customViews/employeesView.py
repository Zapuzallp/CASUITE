import json
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views.generic import DetailView

from home.models import Employee, OfficeDetails
from home.forms import EmployeeForm
import openpyxl
from openpyxl.styles import Font
from django.http import HttpResponse

class EmployeeView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        employees = get_filtered_employees(request)
        offices = OfficeDetails.objects.all()

        per_page = request.GET.get('per_page', 10)

        if per_page == "all":
            per_page = employees.count()
        else:
            try:
                per_page = int(per_page)
            except:
                per_page = 10

        page_number = request.GET.get('page', 1)
        paginator = Paginator(employees, per_page)
        employees_page = paginator.get_page(page_number)

        return render(request, 'employees.html', {
            'employees': employees_page,
            'offices': offices
        })


class AddEmployeeView(LoginRequiredMixin, View):
    """Handle adding and editing an employee"""
    def get(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(Employee, pk=pk)
            
        form = EmployeeForm(instance=instance)
        return render(request, 'add_employee.html', {
            'form': form,
            'is_edit': bool(pk),
            'employee': instance
        })
    
    def post(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(Employee, pk=pk)
            
        form = EmployeeForm(request.POST, request.FILES, instance=instance)
        
        if form.is_valid():
            try:
                employee = form.save()
                action = "updated" if pk else "added"
                messages.success(
                    request,
                    f'Employee {employee.user.first_name} {employee.user.last_name} {action} successfully!'
                )
                return redirect('employee-view')
            except Exception as e:
                messages.error(request, f'Error saving employee: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
        
        return render(request, 'add_employee.html', {
            'form': form,
            'is_edit': bool(pk),
            'employee': instance
        })


# Reusable to both export and employee view
def get_filtered_employees(request):
    user = request.user

    # Safety check
    if not hasattr(user, 'employee') and not user.is_superuser:
        return Employee.objects.none()

    # Role-based access
    if user.is_superuser:
        employees = Employee.objects.all()

    else:
        role = user.employee.role

        if role == 'ADMIN':
            employees = Employee.objects.all()

        elif role == 'BRANCH_MANAGER':
            if user.employee.office_location:
                employees = Employee.objects.filter(
                    office_location=user.employee.office_location
                )
            else:
                employees = Employee.objects.none()
        else:
            return Employee.objects.none()

    # Filters
    query = request.GET.get('q')
    role_filter = request.GET.get('role')
    office = request.GET.get('office')

    if query:
        employees = employees.filter(user__username__icontains=query)

    if role_filter:
        employees = employees.filter(role=role_filter)

    if office:
        employees = employees.filter(office_location_id=office)

    return employees.select_related('user', 'office_location').order_by('user__username')

class EmployeeDetailView(DetailView):
    model = Employee
    template_name = 'employee_details.html'
    context_object_name = 'employee'
    pk_url_kwarg = 'id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        employee = self.get_object()
        user = employee.user

        # Structured fields (like client_fields)
        context['employee_fields'] = [
            # USER INFO
            {"label": "Username", "value": user.username},
            {"label": "First Name", "value": user.first_name},
            {"label": "Last Name", "value": user.last_name},
            {"label": "Email", "value": user.email},

            # EMPLOYEE INFO
            {"label": "Designation", "value": employee.designation},
            {"label": "Role", "value": employee.role},
            {"label": "Office", "value": employee.office_location.office_name if employee.office_location else "-"},
            {"label": "Supervisor", "value": employee.supervisor.get_full_name() if employee.supervisor else "-"},

            # CONTACT
            {"label": "Work Phone", "value": employee.work_phone},
            {"label": "Personal Phone", "value": employee.personal_phone},
            {"label": "Personal Email", "value": employee.personal_email},
            {"label": "Address", "value": employee.address},

            # SYSTEM
            {"label": "Status", "value": "Active" if user.is_active else "Inactive"},
            {"label": "Joined On", "value": user.date_joined},
            {"label": "Created At", "value": employee.created_at},
        ]

        # Leave Summary
        context['leave_summary'] = employee.get_leave_summary()

        return context