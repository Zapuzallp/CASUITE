import json
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator

from home.models import Employee, OfficeDetails
from home.forms import EmployeeForm
class EmployeeView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):

        user = request.user

        # safety check if the user is not employee
        if not hasattr(user, 'employee') and not user.is_superuser:
            return HttpResponseForbidden("Employee profile not found.")

        # Superuser → full access
        if user.is_superuser:
            employees = Employee.objects.all()

        else:
            role = user.employee.role

            # Admin → full access view only
            if role == 'ADMIN':
                employees = Employee.objects.all()

            #  Branch Manager → only their branch view
            elif role == 'BRANCH_MANAGER':
                if user.employee.office_location:
                    employees = Employee.objects.filter(
                        office_location=user.employee.office_location
                    )
                else:
                    employees = Employee.objects.none()

            # Staff → blocked
            else:
                return HttpResponseForbidden("You do not have permission to view this page.")

        #Filters
        query = request.GET.get('q')
        role_filter = request.GET.get('role')
        office = request.GET.get('office')

        if query:
            employees = employees.filter(
                user__username__icontains=query
            )

        if role_filter:
            employees = employees.filter(role=role_filter)

        if office:
            employees = employees.filter(office_location_id=office)

        offices = OfficeDetails.objects.all()

        employees = employees.select_related('user', 'office_location').order_by('-id')

        page_number = request.GET.get('page', 1)

        paginator = Paginator(employees, 10)

        employees_page = paginator.get_page(page_number)

        return render(request, 'employees.html', {
            'employees': employees_page,
            'offices': offices
        })


class AddEmployeeView(LoginRequiredMixin, View):
    """Handle adding a new employee"""
    def get(self, request, *args, **kwargs):
        form = EmployeeForm()
        return render(request, 'add_employee.html', {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = EmployeeForm(request.POST)
        
        if form.is_valid():
            try:
                employee = form.save()
                messages.success(
                    request,
                    f'Employee {employee.user.first_name} {employee.user.last_name} added successfully!'
                )
                return redirect('employee-view')
            except Exception as e:
                messages.error(request, f'Error creating employee: {str(e)}')
                return render(request, 'add_employee.html', {'form': form})
        else:
            messages.error(request, 'Please correct the errors below.')
        
        return render(request, 'add_employee.html', {'form': form})


class EmployeeDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Only superusers can delete employees.")

        employee = get_object_or_404(Employee, pk=pk)
        employee.delete()

        return redirect(request.META.get('HTTP_REFERER', 'employee-view'))