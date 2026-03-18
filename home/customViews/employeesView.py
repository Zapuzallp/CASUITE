from django.http import HttpResponseForbidden
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from home.models import Employee, OfficeDetails
from django.core.paginator import Paginator

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

        employees = employees.select_related('user', 'office_location')

        page_number = request.GET.get('page', 1)

        paginator = Paginator(employees, 10)

        employees_page = paginator.get_page(page_number)

        return render(request, 'employees.html', {
            'employees': employees_page,
            'offices': offices
        })


class EmployeeDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Only superusers can delete employees.")

        employee = get_object_or_404(Employee, pk=pk)
        employee.delete()

        return redirect(request.META.get('HTTP_REFERER', 'employee-view'))