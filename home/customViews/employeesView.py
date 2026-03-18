from home.models import Employee
from home.forms import EmployeeForm
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
import json


class EmployeeView(View):
    """Display list of all employees"""
    def get(self, request, *args, **kwargs):
        employees = Employee.objects.all().select_related('user', 'office_location', 'supervisor')
        return render(request, 'employees.html', {
            'employees': employees
        })


class AddEmployeeView(View):
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

