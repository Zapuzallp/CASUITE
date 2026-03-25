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
import openpyxl
from openpyxl.styles import Font
from django.http import HttpResponse

class EmployeeView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        employees = get_filtered_employees(request)
        offices = OfficeDetails.objects.all()

        page_number = request.GET.get('page', 1)
        paginator = Paginator(employees, 10)
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
                if pk:
                    return redirect('employee-view')
                return redirect('add-employee')
            except Exception as e:
                messages.error(request, f'Error saving employee: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
        
        return render(request, 'add_employee.html', {
            'form': form,
            'is_edit': bool(pk),
            'employee': instance
        })


class EmployeeDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Only superusers can delete employees.")

        employee = get_object_or_404(Employee, pk=pk)
        employee.user.delete()

        return redirect(request.META.get('HTTP_REFERER', 'employee-view'))

class ExportEmployeeView(LoginRequiredMixin, View):
        def get(self, request, *args, **kwargs):
            employees = get_filtered_employees(request)

            # Create workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Employees"

            # Header row
            headers = [
                'First Name', 'Last Name', 'Username', 'Email',
                'Role', 'Office', 'Designation',
                'Personal Phone', 'Work Phone'
            ]

            ws.append(headers)

            # Make header bold
            for cell in ws[1]:
                cell.font = Font(bold=True)

            # Helper for phone formatting
            def format_phone(phone):
                return str(phone) if phone else ''

            # Add data rows
            for emp in employees:
                ws.append([
                    emp.user.first_name or '',
                    emp.user.last_name or '',
                    emp.user.username or '',
                    emp.user.email or '',
                    emp.get_role_display() if hasattr(emp, 'get_role_display') else emp.role,
                    str(emp.office_location) if emp.office_location else '',
                    emp.designation or '',
                    format_phone(emp.personal_phone),
                    format_phone(emp.work_phone),
                ])

            # Auto-adjust column width (simple version)
            for col in ws.columns:
                max_length = 0
                col_letter = col[0].column_letter

                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))

                ws.column_dimensions[col_letter].width = max_length + 2

            # Prepare response
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="employees.xlsx"'

            wb.save(response)

            return response

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

    return employees.select_related('user', 'office_location').order_by('-id')
