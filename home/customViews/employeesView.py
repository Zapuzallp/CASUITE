from home.models import Employee
from django.views import View
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect


class EmployeeView(View):
    def get(self, request, *args, **kwargs):
        employees = Employee.objects.all()
        return render(request, 'employees.html', {'employees': employees})

